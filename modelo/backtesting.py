import requests
import pandas as pd
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


class MotorBacktesting:
    VENTANA = 100
    COMISION = 0.001
    DIAS_ANUALIZACION = 365 
    
    # REEMPLAZAMOS EL PORCENTAJE FIJO POR UN MULTIPLICADOR ESTADÍSTICO
    # 2.5x a 3.0x el ATR es el estándar en sistemas tendenciales
    ATR_MULTIPLIER = 2.5 

    def __init__(self):
        self.capital_inicial = 1000.0
        self.capital_actual = self.capital_inicial
        self.operaciones = 0
        self.ganadoras = 0
        self.stops_activados = 0

    def _proyectar_tendencia(self, closes):
        """
        Regresión lineal vectorizada. Devuelve la PENDIENTE para evaluar 
        la dirección de la tendencia, eliminando el ruido del precio diario.
        """
        ventana = self.VENTANA
        x = np.arange(ventana)
        sum_x = x.sum()
        sum_x2 = (x ** 2).sum()
        denom = ventana * sum_x2 - sum_x ** 2

        bloques = sliding_window_view(closes, ventana)
        sum_y = bloques.sum(axis=1)
        sum_xy = (bloques * x).sum(axis=1)

        pendiente = (ventana * sum_xy - sum_x * sum_y) / denom
        return pendiente

    def _calcular_metricas_riesgo(self, equity_curve, closes_periodo):
        """
        Calcula métricas de riesgo-ajustado a partir de la curva de equity diaria.
        """
        equity = np.array(equity_curve, dtype=float)
        retornos_diarios = np.diff(equity) / equity[:-1]

        media = retornos_diarios.mean()
        std_total = retornos_diarios.std()
        sharpe = (media / std_total) * np.sqrt(self.DIAS_ANUALIZACION) if std_total > 0 else 0.0

        retornos_negativos = retornos_diarios[retornos_diarios < 0]
        std_downside = retornos_negativos.std() if len(retornos_negativos) > 0 else 0.0
        sortino = (media / std_downside) * np.sqrt(self.DIAS_ANUALIZACION) if std_downside > 0 else 0.0

        maximo_acumulado = np.maximum.accumulate(equity)
        drawdown = (equity - maximo_acumulado) / maximo_acumulado
        max_drawdown_pct = drawdown.min() * 100

        precio_inicio = closes_periodo[0]
        precio_fin = closes_periodo[-1]
        buyhold_pct = (precio_fin - precio_inicio) / precio_inicio * 100

        return {
            "sharpe": round(sharpe, 2),
            "sortino": round(sortino, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "buyhold_pct": round(buyhold_pct, 2),
        }

    def ejecutar_simulacion(self, dias=500):
        dias = min(dias, 1000)
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": "BTCUSDT", "interval": "1d", "limit": dias}
            response = requests.get(url, params=params, timeout=10).json()

            df = pd.DataFrame(response, columns=[
                'Fecha', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime',
                'QuoteVolume', 'Trades', 'TakerBuyBase', 'TakerBuyQuote', 'Ignore'
            ])
            df['Close'] = df['Close'].astype(float)
            df['High'] = df['High'].astype(float)
            df['Low'] = df['Low'].astype(float)
            df['Fecha'] = pd.to_datetime(df['Fecha'], unit='ms')
            df['Mes'] = df['Fecha'].dt.month

            # --- NUEVO: CÁLCULO ESTADÍSTICO DE VOLATILIDAD (ATR) Y MOMENTUM (SMA 20) ---
            df['Prev_Close'] = df['Close'].shift(1)
            df['TR1'] = df['High'] - df['Low']
            df['TR2'] = (df['High'] - df['Prev_Close']).abs()
            df['TR3'] = (df['Low'] - df['Prev_Close']).abs()
            df['TR'] = df[['TR1', 'TR2', 'TR3']].max(axis=1)
            df['ATR'] = df['TR'].rolling(window=14).mean().bfill()
            
            # ---> NUEVO 1: Calculamos la Media Móvil de 20 días para salidas rápidas
            df['SMA_20'] = df['Close'].rolling(window=20).mean().bfill()
            # -------------------------------------------------------

            probs = {1: 57.14, 2: 42.86, 3: 71.43, 4: 57.14, 5: 42.86, 6: 28.57,
                     7: 85.71, 8: 16.67, 9: 50.00, 10: 83.33, 11: 50.00, 12: 50.00}

            closes = df['Close'].values
            if len(closes) <= self.VENTANA + 1:
                return {"exito": False, "error": "No hay suficientes velas para simular."}

            pendientes = self._proyectar_tendencia(closes)

            posicion_abierta = False
            precio_compra = 0
            precio_maximo_en_posicion = 0
            capital_base = self.capital_inicial 
            equity_curve = []
            
            dias_cooldown = 0 
            nivel_stop_dinamico = 0 # Inicializamos la variable de riesgo

            for idx in range(len(pendientes) - 1):
                i = idx + self.VENTANA
                if i >= len(df) - 1:
                    break

                pendiente_hoy = pendientes[idx]
                precio_hoy = df['Close'].iloc[i]
                dia_high = df['High'].iloc[i]
                dia_low = df['Low'].iloc[i]
                mes_hoy = df['Mes'].iloc[i]
                atr_hoy = df['ATR'].iloc[i] # Volatilidad de hoy
                
                # ---> NUEVO 2: Obtenemos el valor de la SMA_20 en el día actual
                sma_20_hoy = df['SMA_20'].iloc[i] 
                prob_mes = probs.get(mes_hoy, 50)

                tendencia_alcista = pendiente_hoy > 0

                en_cooldown = dias_cooldown > 0
                if en_cooldown:
                    dias_cooldown -= 1

                if not posicion_abierta:
                    # ---> CORRECCIÓN: Entramos basados SOLO en la macro tendencia y estacionalidad.
                    if tendencia_alcista and prob_mes >= 50 and not en_cooldown:
                        posicion_abierta = True
                        precio_compra = precio_hoy * (1 + self.COMISION)
                        precio_maximo_en_posicion = precio_compra
                        capital_base = self.capital_actual
                        
                        # El stop inicial se calcula restando volatilidad al precio de entrada
                        nivel_stop_dinamico = precio_compra - (atr_hoy * self.ATR_MULTIPLIER)

                else:
                    # El nivel candidato sube si el precio sube, adaptándose a la volatilidad
                    nivel_stop_candidato = precio_maximo_en_posicion - (atr_hoy * self.ATR_MULTIPLIER)
                    
                    # El stop NUNCA baja. Solo usamos el nuevo candidato si es mayor al anterior.
                    nivel_stop_dinamico = max(nivel_stop_dinamico, nivel_stop_candidato)

                    # Prioridad 1: Salida por Stop-Loss
                    if dia_low <= nivel_stop_dinamico:
                        posicion_abierta = False
                        precio_venta = nivel_stop_dinamico * (1 - self.COMISION)
                        rendimiento = (precio_venta - precio_compra) / precio_compra
                        self.capital_actual = capital_base * (1 + rendimiento)
                        self.operaciones += 1
                        self.stops_activados += 1
                        if rendimiento > 0:
                            self.ganadoras += 1
                        
                        dias_cooldown = 5

                    # ---> NUEVO 4: Agregamos "precio_hoy < sma_20_hoy" para salir rápido si se pierde el impulso
                    elif not tendencia_alcista or prob_mes < 50 or precio_hoy < sma_20_hoy:
                        posicion_abierta = False
                        precio_venta = precio_hoy * (1 - self.COMISION)
                        rendimiento = (precio_venta - precio_compra) / precio_compra
                        self.capital_actual = capital_base * (1 + rendimiento)
                        self.operaciones += 1
                        if rendimiento > 0:
                            self.ganadoras += 1

                    if posicion_abierta:
                        precio_maximo_en_posicion = max(precio_maximo_en_posicion, dia_high)

                if posicion_abierta:
                    equity_hoy = capital_base * (precio_hoy / precio_compra)
                else:
                    equity_hoy = self.capital_actual
                equity_curve.append(equity_hoy)

            if posicion_abierta:
                precio_venta = df['Close'].iloc[-1] * (1 - self.COMISION)
                rendimiento = (precio_venta - precio_compra) / precio_compra
                self.capital_actual = capital_base * (1 + rendimiento)
                self.operaciones += 1
                if rendimiento > 0:
                    self.ganadoras += 1
                equity_curve[-1] = self.capital_actual

            if len(equity_curve) < 2:
                return {"exito": False, "error": "Periodo demasiado corto."}

            win_rate_final = (self.ganadoras / self.operaciones * 100) if self.operaciones > 0 else 0
            rendimiento_pct = ((self.capital_actual - self.capital_inicial) / self.capital_inicial) * 100

            closes_periodo = closes[self.VENTANA:self.VENTANA + len(equity_curve)]
            metricas_riesgo = self._calcular_metricas_riesgo(equity_curve, closes_periodo)

            return {
                "exito": True,
                "capital_final": self.capital_actual,
                "rendimiento_pct": rendimiento_pct,
                "operaciones": self.operaciones,
                "win_rate": win_rate_final,
                "stops_activados": self.stops_activados,
                **metricas_riesgo,
            }

        except Exception as e:
            return {"exito": False, "error": str(e)}