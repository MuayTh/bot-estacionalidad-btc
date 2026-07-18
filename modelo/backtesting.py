import requests
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

class MotorBacktesting:
    def __init__(self):
        self.capital_inicial = 1000.0
        self.capital_actual = self.capital_inicial
        self.operaciones = 0
        self.ganadoras = 0

    def ejecutar_simulacion(self):
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 500}
            response = requests.get(url, params=params, timeout=10).json()
            
            df = pd.DataFrame(response, columns=['Fecha', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime', 'QuoteVolume', 'Trades', 'TakerBuyBase', 'TakerBuyQuote', 'Ignore'])
            df['Close'] = df['Close'].astype(float)
            df['Fecha'] = pd.to_datetime(df['Fecha'], unit='ms')
            df['Mes'] = df['Fecha'].dt.month

            # --- NUEVO: CÁLCULO DEL RSI HISTÓRICO ---
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI'] = 100 - (100 / (1 + rs))

            probs = {1: 57.14, 2: 42.86, 3: 71.43, 4: 57.14, 5: 42.86, 6: 28.57,
                     7: 85.71, 8: 16.67, 9: 50.00, 10: 83.33, 11: 50.00, 12: 50.00}

            posicion_abierta = False
            precio_compra = 0

            for i in range(100, len(df) - 1):
                ventana = df.iloc[i-100:i].copy()
                ventana['Dias'] = np.arange(len(ventana))
                X = ventana[['Dias']]
                y = ventana['Close']
                
                modelo = LinearRegression()
                modelo.fit(X, y)
                
                X_pred = pd.DataFrame([[100]], columns=['Dias'])
                prediccion = modelo.predict(X_pred)[0]
                
                precio_hoy = df['Close'].iloc[i]
                mes_hoy = df['Mes'].iloc[i]
                rsi_hoy = df['RSI'].iloc[i] # Sacamos el RSI de ese día específico
                prob_mes = probs.get(mes_hoy, 50)
                
                tendencia_alcista = prediccion > precio_hoy

                # REGLAS DEL SISTEMA (AHORA INCLUYEN EL RSI)
                if tendencia_alcista and prob_mes >= 50 and rsi_hoy <= 70 and not posicion_abierta:
                    # Todo alineado y el precio no está inflado
                    posicion_abierta = True
                    precio_compra = precio_hoy
                
                elif (not tendencia_alcista or prob_mes < 50 or rsi_hoy > 70) and posicion_abierta:
                    # Vendemos si hay peligro o si el mercado se sobrecompró
                    posicion_abierta = False
                    rendimiento = (precio_hoy - precio_compra) / precio_compra
                    self.capital_actual += self.capital_actual * rendimiento
                    self.operaciones += 1
                    if rendimiento > 0:
                        self.ganadoras += 1

            if posicion_abierta:
                rendimiento = (df['Close'].iloc[-1] - precio_compra) / precio_compra
                self.capital_actual += self.capital_actual * rendimiento
                self.operaciones += 1
                if rendimiento > 0:
                    self.ganadoras += 1

            win_rate_final = (self.ganadoras / self.operaciones * 100) if self.operaciones > 0 else 0
            rendimiento_pct = ((self.capital_actual - self.capital_inicial) / self.capital_inicial) * 100

            return True, self.capital_actual, rendimiento_pct, self.operaciones, win_rate_final
            
        except Exception as e:
            return False, str(e), 0, 0, 0