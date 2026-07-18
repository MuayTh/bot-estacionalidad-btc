import requests
import pandas as pd
import numpy as np
import datetime
from sklearn.linear_model import LinearRegression

class ModeloBitcoin:
    def __init__(self):
        self.estado_conexion = "Desconectado"
        self.precio_actual = 0
        self.prediccion_mañana = 0
        self.tendencia_ia = ""
        self.probabilidad_mes = 0
        self.riesgo_estacional = ""
        self.rsi_actual = 50.0 # Nueva variable para el RSI

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
            
            # --- NUEVO: CÁLCULO MATEMÁTICO DEL RSI ---
            delta = df['Close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            df['RSI'] = 100 - (100 / (1 + rs))
            self.rsi_actual = df['RSI'].iloc[-1]
            # -----------------------------------------
            
            df['Dias'] = np.arange(len(df))
            X = df[['Dias']]
            y = df['Close']
            
            modelo = LinearRegression()
            modelo.fit(X, y)
            
            dia_mañana = np.array([[len(df)]])
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