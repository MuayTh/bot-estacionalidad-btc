import requests
import pandas as pd
import numpy as np
import datetime
from sklearn.linear_model import LinearRegression
import websocket
import json
import threading
import time

class ModeloBitcoin:
    def __init__(self):
        self.estado_conexion = "Desconectado"
        self.precio_actual = 0
        self.prediccion_mañana = 0
        self.tendencia_ia = ""
        self.probabilidad_mes = 0
        self.riesgo_estacional = ""
        self.rsi_actual = 50.0 
        self.ws = None 
        self.callback_precio = None 

    def evaluar_estacionalidad(self):
        """
        Calcula el % histórico de meses alcistas por mes calendario usando
        TODO el historial disponible de BTCUSDT en Binance (desde 2017),
        en vez de una tabla fija basada en 2020-2026.

        Motivo del cambio: con solo 6-7 años de muestra, un porcentaje como
        "85.71%" equivale a 6 aciertos sobre 7 observaciones -> un solo año
        distinto mueve el porcentaje ~14 puntos. Ampliar la ventana a ~9 años
        no elimina el problema de fondo (la estacionalidad de BTC sigue
        siendo una muestra pequeña en términos estadísticos), pero sí reduce
        el sobreajuste a la casualidad de un puñado de años específicos.
        """
        probabilidades_historicas = None
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                "symbol": "BTCUSDT",
                "interval": "1M",
                "startTime": 1502928000000,  # ago-2017: listado de BTCUSDT en Binance
                "limit": 1000
            }
            response = requests.get(url, params=params, timeout=10).json()

            df = pd.DataFrame(response, columns=[
                'Fecha', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime',
                'QuoteVolume', 'Trades', 'TakerBuyBase', 'TakerBuyQuote', 'Ignore'
            ])
            df['Open'] = df['Open'].astype(float)
            df['Close'] = df['Close'].astype(float)
            df['Fecha'] = pd.to_datetime(df['Fecha'], unit='ms')
            df['Mes'] = df['Fecha'].dt.month
            df['Alcista'] = df['Close'] > df['Open']

            # Descartamos el mes en curso: aún no ha cerrado, no es una observación válida
            hoy = datetime.datetime.now()
            df = df[df['Fecha'] < datetime.datetime(hoy.year, hoy.month, 1)]

            stats = df.groupby('Mes')['Alcista'].agg(['mean', 'count'])
            probabilidades_historicas = (stats['mean'] * 100).round(2).to_dict()
            self.muestra_por_mes = stats['count'].to_dict()
            self._ultimas_probs = probabilidades_historicas  # cache para fallback

        except Exception as e:
            # Si falla la descarga, reusamos el último cálculo válido (o neutral si nunca hubo uno)
            probabilidades_historicas = getattr(self, '_ultimas_probs', {m: 50.0 for m in range(1, 13)})
            self.muestra_por_mes = getattr(self, 'muestra_por_mes', {})
            print(f"⚠️ No se pudo recalcular estacionalidad, usando último valor conocido: {e}")

        mes_actual = datetime.datetime.now().month
        self.probabilidad_mes = probabilidades_historicas.get(mes_actual, 50.0)
        self.muestra_mes_actual = self.muestra_por_mes.get(mes_actual, 0)

        if self.probabilidad_mes >= 70:
            self.riesgo_estacional = "Favorable (Bajo Riesgo)"
        elif self.probabilidad_mes <= 40:
            self.riesgo_estacional = "Peligroso (Alto Riesgo)"
        else:
            self.riesgo_estacional = "Neutral (Riesgo Medio)"

    def obtener_datos_entrenar_modelo(self):
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 100}
            response = requests.get(url, params=params, timeout=5).json()
            
            df = pd.DataFrame(response, columns=['Fecha', 'Open', 'High', 'Low', 'Close', 'Volume', 'CloseTime', 'QuoteVolume', 'Trades', 'TakerBuyBase', 'TakerBuyQuote', 'Ignore'])
            df['Close'] = df['Close'].astype(float)
            self.precio_actual = df['Close'].iloc[-1]
            
            # --- CÁLCULO DE RSI ---
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI'] = 100 - (100 / (1 + rs))
            self.rsi_actual = df['RSI'].iloc[-1]
            
            # --- NUEVO: CÁLCULO DE MEDIA MÓVIL (SMA_7) ---
            df['SMA_7'] = df['Close'].rolling(window=7).mean()
            
            # Limpiamos los valores vacíos (NaN) que deja el RSI y la SMA en las primeras filas
            df.dropna(inplace=True)
            
            # Enumeramos los días después de limpiar los datos
            df['Dias'] = np.arange(len(df))
            
            # --- NUEVO: ENTRENAMIENTO MULTIVARIABLE ---
            # Ahora la IA aprende cruzando 3 dimensiones: Tiempo, Fuerza (RSI) y Tendencia (SMA_7)
            X = df[['Dias', 'RSI', 'SMA_7']]
            y = df['Close']
            
            modelo = LinearRegression()
            modelo.fit(X, y)

            # Transparencia: qué tan bien ajusta la regresión a los datos.
            # IMPORTANTE: un R² alto en datos de entrenamiento NO implica poder
            # predictivo real sobre el precio futuro de BTC (activo altamente no lineal).
            # Este valor es solo un indicador de ajuste, no una garantía de acierto.
            self.confianza_modelo = modelo.score(X, y)
            
            # --- NUEVA LÓGICA: SEÑAL POR PENDIENTE ---
            # El coeficiente 0 corresponde a la variable 'Dias'. 
            # Nos dice la inclinación de la tendencia descontando el ruido diario.
            pendiente_tendencia = modelo.coef_[0]
            
            # Mantenemos el cálculo de la predicción de mañana solo para mostrarlo en la interfaz
            dia_mañana = pd.DataFrame({'Dias': [len(df)], 'RSI': [self.rsi_actual], 'SMA_7': [df['SMA_7'].iloc[-1]]})
            self.prediccion_mañana = modelo.predict(dia_mañana)[0]
            
            # La decisión ahora depende de la estructura de la tendencia, no de un punto aislado
            if pendiente_tendencia > 0:
                self.tendencia_ia = "ALCISTA (Pendiente Positiva)"
            else:
                self.tendencia_ia = "BAJISTA (Pendiente Negativa)"
                
            self.estado_conexion = "Datos sincronizados y modelo entrenado."
            self.evaluar_estacionalidad()
            return True
            
        except Exception as e:
            self.estado_conexion = f"Error de conexión: {e}"
            return False

    # --- TÚNEL WEBSOCKET (con reconexión automática) ---
    def iniciar_stream_precio(self, callback):
        self.callback_precio = callback
        self._stream_activo = True
        # Abrimos el túnel en un "hilo" paralelo para que la interfaz gráfica no se congele
        hilo = threading.Thread(target=self._conectar_websocket)
        hilo.daemon = True
        hilo.start()

    def detener_stream_precio(self):
        """Permite cerrar el stream de forma limpia (ej. al cerrar la app)."""
        self._stream_activo = False
        if self.ws:
            self.ws.close()

    def _conectar_websocket(self):
        url_ws = "wss://stream.binance.com:9443/ws/btcusdt@ticker"
        intentos = 0

        # Bucle de reconexión: si el WebSocket se cae (caída de red, reinicio
        # del servidor de Binance, etc.) se reintenta con backoff exponencial
        # en vez de dejar el precio en vivo congelado silenciosamente.
        while getattr(self, '_stream_activo', True):
            try:
                self.ws = websocket.WebSocketApp(
                    url_ws,
                    on_message=self._al_recibir_mensaje,
                    on_error=self._al_ocurrir_error,
                    on_close=self._al_cerrar_conexion
                )
                intentos = 0
                self.ws.run_forever()
            except Exception as e:
                print(f"⚠️ Excepción en WebSocket: {e}")

            if not getattr(self, '_stream_activo', True):
                break

            intentos += 1
            espera = min(30, 2 ** intentos)  # backoff exponencial, tope de 30s
            print(f"🔄 WebSocket desconectado. Reintentando en {espera}s (intento {intentos})...")
            time.sleep(espera)

    def _al_ocurrir_error(self, ws, error):
        print(f"⚠️ Error de WebSocket: {error}")

    def _al_cerrar_conexion(self, ws, close_status_code, close_msg):
        print("🔌 Conexión WebSocket cerrada.")

    def _al_recibir_mensaje(self, ws, mensaje):
        datos = json.loads(mensaje)
        precio_en_vivo = float(datos['c']) # 'c' significa Current/Close price
        self.precio_actual = precio_en_vivo
        if self.callback_precio:
            self.callback_precio(precio_en_vivo)