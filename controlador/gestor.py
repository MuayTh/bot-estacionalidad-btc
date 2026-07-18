from modelo.motor_ia import ModeloBitcoin
from modelo.backtesting import MotorBacktesting
from modelo.dao import OperacionDAO  # NUEVA IMPORTACIÓN
from vista.interfaz import VistaTerminal

class ControladorTerminal:
    def __init__(self, root):
        self.modelo = ModeloBitcoin()
        self.simulador = MotorBacktesting()
        self.dao = OperacionDAO()  # INICIALIZAMOS EL DAO
        self.vista = VistaTerminal(root, self)

    def calcular_decision_final(self):
        tendencia = self.modelo.tendencia_ia
        probabilidad = self.modelo.probabilidad_mes
        rsi = self.modelo.rsi_actual 

        if "ALCISTA" in tendencia and probabilidad >= 50:
            if rsi > 70:
                return f" BLOQUEADA (RSI en {rsi:.1f} - Sobrecomprado) ", "#f3ba2f"
            else:
                return f" COMPRA APROBADA (RSI {rsi:.1f} Óptimo) ", "#4caf50"
                
        elif "BAJISTA" in tendencia and probabilidad < 50:
            if rsi < 30:
                return f" BLOQUEADA (RSI en {rsi:.1f} - Sobrevendido) ", "#f3ba2f"
            else:
                return f" VENTA APROBADA (RSI {rsi:.1f} Óptimo) ", "#ff4c4c"
        else:
            return " OPERACIÓN BLOQUEADA (Señales Mixtas / Riesgo) ", "#f3ba2f"

    def iniciar_sistema(self):
        self.vista.lbl_decision.config(text="CALCULANDO...", foreground="#ffffff")
        self.vista.root.update()
        
        exito = self.modelo.obtener_datos_entrenar_modelo()
        
        if exito:
            decision, color = self.calcular_decision_final()
            self.vista.actualizar_pantalla(exito, self.modelo, decision, color)
            
            # Encendemos el WebSocket
            self.modelo.iniciar_stream_precio(self.actualizar_precio_interfaz)
            
            # --- NUEVO: GUARDAMOS EN BASE DE DATOS ---
            # Limpiamos el texto de la decisión para que se vea bien en la BD
            decision_limpia = decision.replace(" ", "", 1).strip()
            self.dao.guardar_decision(self.modelo.precio_actual, self.modelo.rsi_actual, decision_limpia)

    def actualizar_precio_interfaz(self, precio_nuevo):
        self.vista.root.after(0, lambda: self.vista.lbl_precio.config(text=f"Precio Actual: ${precio_nuevo:,.2f}"))

    def iniciar_simulacion(self):
        self.vista.lbl_sim_resultado.config(text="Procesando 500 días de IA histórica...", foreground="#f3ba2f")
        self.vista.root.update()
        
        self.simulador = MotorBacktesting() 
        exito, capital, rendimiento, operaciones, win_rate = self.simulador.ejecutar_simulacion()
        self.vista.actualizar_simulacion(exito, capital, rendimiento, operaciones, win_rate)