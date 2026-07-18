import requests
import pandas as pd
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


class MotorBacktesting:
    VENTANA = 100
    # Comisión spot estándar de Binance (0.1%), aplicada en compra y en venta.
    # Sin esto, el rendimiento simulado es artificialmente optimista.
    COMISION = 0.001

    def __init__(self):
        self.capital_inicial = 1000.0
        self.capital_actual = self.capital_inicial
        self.operaciones = 0
        self.ganadoras = 0

    def _proyectar_precios(self, closes):
        """
        Para cada ventana de 100 días, calcula la proyección de precio
        (regresión lineal sobre esos 100 días) usando la fórmula cerrada de
        OLS en vez de reentrenar un modelo de sklearn en cada iteración.

        Como el eje X siempre es [0..99] (fijo), sum(x) y sum(x^2) son
        constantes y toda la operación se vectoriza con numpy sobre las
        ~400 ventanas de una vez, en lugar de instanciar y entrenar ~400
        modelos de LinearRegression uno por uno dentro de un for loop.
        """
        ventana = self.VENTANA
        x = np.arange(ventana)
        sum_x = x.sum()
        sum_x2 = (x ** 2).sum()
        denom = ventana * sum_x2 - sum_x ** 2

        bloques = sliding_window_view(closes, ventana)  # forma: (n-ventana+1, ventana)
        sum_y = bloques.sum(axis=1)
        sum_xy = (bloques * x).sum(axis=1)

        pendiente = (ventana * sum_xy - sum_x * sum_y) / denom
        intercepto = (sum_y - pendiente * sum_x) / ventana

        # Proyección para el día siguiente al final de cada ventana (x = ventana)
        return intercepto + pendiente * ventana

    def ejecutar_simulacion(self):
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 500}
            response = requests.get(url, params=params, timeout=10).json()

            df = pd.DataFrame(response, columns=[
                'Fecha', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime',
                'QuoteVolume', 'Trades', 'TakerBuyBase', 'TakerBuyQuote', 'Ignore'
            ])
            df['Close'] = df['Close'].astype(float)
            df['Fecha'] = pd.to_datetime(df['Fecha'], unit='ms')
            df['Mes'] = df['Fecha'].dt.month

            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI'] = 100 - (100 / (1 + rs))

            probs = {1: 57.14, 2: 42.86, 3: 71.43, 4: 57.14, 5: 42.86, 6: 28.57,
                     7: 85.71, 8: 16.67, 9: 50.00, 10: 83.33, 11: 50.00, 12: 50.00}

            closes = df['Close'].values
            if len(closes) <= self.VENTANA + 1:
                return False, "No hay suficientes velas para simular.", 0, 0, 0

            proyecciones = self._proyectar_precios(closes)

            posicion_abierta = False
            precio_compra = 0

            # Este loop ya NO entrena modelos (eso se vectorizó arriba); solo
            # recorre secuencialmente para aplicar la lógica de entrada/salida,
            # que sí depende del estado (si hay posición abierta o no).
            for idx in range(len(proyecciones) - 1):
                i = idx + self.VENTANA
                if i >= len(df) - 1:
                    break

                prediccion = proyecciones[idx]
                precio_hoy = df['Close'].iloc[i]
                mes_hoy = df['Mes'].iloc[i]
                rsi_hoy = df['RSI'].iloc[i]
                prob_mes = probs.get(mes_hoy, 50)

                tendencia_alcista = prediccion > precio_hoy

                if tendencia_alcista and prob_mes >= 50 and rsi_hoy <= 70 and not posicion_abierta:
                    posicion_abierta = True
                    precio_compra = precio_hoy * (1 + self.COMISION)  # comisión de entrada

                elif (not tendencia_alcista or prob_mes < 50 or rsi_hoy > 70) and posicion_abierta:
                    posicion_abierta = False
                    precio_venta = precio_hoy * (1 - self.COMISION)  # comisión de salida
                    rendimiento = (precio_venta - precio_compra) / precio_compra
                    self.capital_actual += self.capital_actual * rendimiento
                    self.operaciones += 1
                    if rendimiento > 0:
                        self.ganadoras += 1

            if posicion_abierta:
                precio_venta = df['Close'].iloc[-1] * (1 - self.COMISION)
                rendimiento = (precio_venta - precio_compra) / precio_compra
                self.capital_actual += self.capital_actual * rendimiento
                self.operaciones += 1
                if rendimiento > 0:
                    self.ganadoras += 1

            win_rate_final = (self.ganadoras / self.operaciones * 100) if self.operaciones > 0 else 0
            rendimiento_pct = ((self.capital_actual - self.capital_inicial) / self.capital_inicial) * 100

            return True, self.capital_actual, rendimiento_pct, self.operaciones, win_rate_final

        except Exception as e:
            return False, str(e), 0, 0, 0