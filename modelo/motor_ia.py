import requests
import pandas as pd
import numpy as np
import datetime
from sklearn.linear_model import LinearRegression
import websocket
import json
import threading

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
        probabilidades_historicas = {
            1: 57.14, 2: 42.86, 3: 71.43, 4: 57.14, 5: 42.86, 6: 28.57,
            7: 85.71, 8: 16.67, 9: 50.00, 10: 83.33, 11: 50.00, 12: 50.00
        }
        mes_actual = datetime.datetime.now().month
        self.probabilidad_mes = probabilidades_historicas.get(mes_actual, 50.0)
        
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
            
            # --- NUEVO: PREDICCIÓN ACTUALIZADA ---
            # Para predecir mañana, le damos el día siguiente más los últimos datos conocidos
            dia_mañana = pd.DataFrame({
                'Dias': [len(df)],
                'RSI': [self.rsi_actual],
                'SMA_7': [df['SMA_7'].iloc[-1]]
            })
            
            self.prediccion_mañana = modelo.predict(dia_mañana)[0]
            
            if self.prediccion_mañana > self.precio_actual:
                self.tendencia_ia = "ALCISTA (Proyección Positiva)"
            else:
                self.tendencia_ia = "BAJISTA (Proyección Negativa)"
                
            self.estado_conexion = "Datos sincronizados y modelo entrenado."
            self.evaluar_estacionalidad()
            return True
            
        except Exception as e:
            self.estado_conexion = f"Error de conexión: {e}"
            return False

    # --- NUEVO: TÚNEL WEBSOCKET ---
    def iniciar_stream_precio(self, callback):
        self.callback_precio = callback
        # Abrimos el túnel en un "hilo" paralelo para que la interfaz gráfica no se congele
        hilo = threading.Thread(target=self._conectar_websocket)
        hilo.daemon = True
        hilo.start()

    def _conectar_websocket(self):
        url_ws = "wss://stream.binance.com:9443/ws/btcusdt@ticker"
        self.ws = websocket.WebSocketApp(
            url_ws,
            on_message=self._al_recibir_mensaje
        )
        self.ws.run_forever()

    def _al_recibir_mensaje(self, ws, mensaje):
        datos = json.loads(mensaje)
        precio_en_vivo = float(datos['c']) # 'c' significa Current/Close price
        self.precio_actual = precio_en_vivo
        if self.callback_precio:
            self.callback_precio(precio_en_vivo)