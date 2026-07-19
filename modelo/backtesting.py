import requests
import pandas as pd
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


class MotorBacktesting:
    VENTANA = 100
    # Comisión spot estándar de Binance (0.1%), aplicada en compra y en venta.
    COMISION = 0.001
    DIAS_ANUALIZACION = 365  # cripto opera todos los días del año, no 252 como bolsa
    # Un TRAILING stop necesita más margen que uno fijo desde la entrada:
    # como se recalcula contra el máximo reciente todos los días, un % muy
    # ajustado se activa con el ruido normal de BTC (que se mueve 3-5% en un
    # solo día sin que eso sea una reversión real de tendencia).
    STOP_LOSS_PCT = 0.05

    def __init__(self):
        self.capital_inicial = 1000.0
        self.capital_actual = self.capital_inicial
        self.operaciones = 0
        self.ganadoras = 0
        self.stops_activados = 0

    def _proyectar_precios(self, closes):
        """
        Regresión lineal vectorizada (fórmula OLS cerrada) sobre cada ventana
        de 100 días, en vez de reentrenar un modelo de sklearn por iteración.
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
        intercepto = (sum_y - pendiente * sum_x) / ventana

        return intercepto + pendiente * ventana

    def _calcular_metricas_riesgo(self, equity_curve, closes_periodo):
        """
        Calcula métricas de riesgo-ajustado a partir de la curva de equity
        diaria (mark-to-market) de la estrategia, y la compara contra
        simplemente comprar y mantener BTC en el mismo periodo.

        - Sharpe: retorno promedio / volatilidad total (penaliza cualquier
          volatilidad, buena o mala).
        - Sortino: retorno promedio / volatilidad SOLO de los días negativos
          (más justo: no castiga la volatilidad al alza).
        - Max Drawdown: la peor caída desde un máximo histórico de la curva.
        - Buy & Hold: qué hubiera pasado si solo comprabas BTC al inicio del
          periodo y lo mantenías, sin ninguna estrategia. Es el benchmark
          mínimo que cualquier estrategia activa debería superar.
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
        # Nota: 1000 es el máximo de velas que Binance permite traer en una
        # sola llamada a /klines; para ventanas más largas habría que paginar
        # con múltiples requests (startTime/endTime), no implementado aquí.
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
                return {"exito": False, "error": "No hay suficientes velas para simular."}

            proyecciones = self._proyectar_precios(closes)

            posicion_abierta = False
            precio_compra = 0
            precio_maximo_en_posicion = 0
            capital_base = self.capital_inicial  # capital al inicio del trade actual (o capital actual si está flat)
            equity_curve = []

            for idx in range(len(proyecciones) - 1):
                i = idx + self.VENTANA
                if i >= len(df) - 1:
                    break

                prediccion = proyecciones[idx]
                precio_hoy = df['Close'].iloc[i]
                dia_high = df['High'].iloc[i]
                dia_low = df['Low'].iloc[i]
                mes_hoy = df['Mes'].iloc[i]
                rsi_hoy = df['RSI'].iloc[i]
                prob_mes = probs.get(mes_hoy, 50)

                tendencia_alcista = prediccion > precio_hoy

                if not posicion_abierta:
                    if tendencia_alcista and prob_mes >= 50 and rsi_hoy <= 70:
                        posicion_abierta = True
                        precio_compra = precio_hoy * (1 + self.COMISION)
                        precio_maximo_en_posicion = precio_compra
                        capital_base = self.capital_actual

                else:
                    # Trailing stop: el nivel de protección sube junto con el
                    # máximo alcanzado desde la entrada, en vez de quedar fijo
                    # en el precio de compra. Esto deja correr las ganancias
                    # en tendencias fuertes (no te saca solo por una corrección
                    # normal) mientras sigue protegiendo ante una reversión real.
                    #
                    # IMPORTANTE: el nivel de stop de HOY se calcula con el
                    # máximo hasta AYER, no con el máximo de hoy. Si usáramos
                    # el High de hoy para mover el stop y en la misma pasada
                    # comparáramos el Low de hoy contra ese stop recién movido,
                    # cualquier día con rango High-Low amplio (común en BTC,
                    # sin ser una reversión real) se auto-activaría el stop.
                    nivel_stop = precio_maximo_en_posicion * (1 - self.STOP_LOSS_PCT)

                    # Prioridad 1: stop-loss. Se revisa contra el mínimo del día
                    # (no el cierre) porque en un desplome intradía el precio pudo
                    # tocar el stop y recuperarse antes del cierre; ignorar eso
                    # subestima el riesgo real de la estrategia.
                    if dia_low <= nivel_stop:
                        posicion_abierta = False
                        precio_venta = nivel_stop * (1 - self.COMISION)
                        rendimiento = (precio_venta - precio_compra) / precio_compra
                        self.capital_actual = capital_base * (1 + rendimiento)
                        self.operaciones += 1
                        self.stops_activados += 1
                        if rendimiento > 0:
                            self.ganadoras += 1

                    # Prioridad 2: salida normal por cambio de señal
                    elif not tendencia_alcista or prob_mes < 50 or rsi_hoy > 70:
                        posicion_abierta = False
                        precio_venta = precio_hoy * (1 - self.COMISION)
                        rendimiento = (precio_venta - precio_compra) / precio_compra
                        self.capital_actual = capital_base * (1 + rendimiento)
                        self.operaciones += 1
                        if rendimiento > 0:
                            self.ganadoras += 1

                    # La posición sigue abierta: recién ahora actualizamos el
                    # máximo con el High de hoy, para que cuente a partir de MAÑANA.
                    if posicion_abierta:
                        precio_maximo_en_posicion = max(precio_maximo_en_posicion, dia_high)

                # Equity "mark-to-market": si hay posición abierta, el valor del
                # día refleja el precio actual (no solo lo realizado al cerrar).
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
                return {"exito": False, "error": "Periodo demasiado corto para calcular métricas de riesgo."}

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