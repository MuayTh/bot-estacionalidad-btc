from modelo.motor_ia import ModeloBitcoin
from modelo.backtesting import MotorBacktesting
from modelo.dao import OperacionDAO
from modelo.autenticacion import GestorCredenciales
from modelo.ejecucion import GestorOrdenes  # NUEVA IMPORTACIÓN
from vista.interfaz import VistaTerminal

class ControladorTerminal:
    def __init__(self, root):
        self.modelo = ModeloBitcoin()
        self.simulador = MotorBacktesting()
        self.dao = OperacionDAO()
        self.auth = GestorCredenciales()
        self.ejecutor = GestorOrdenes()  # INICIALIZAMOS EL EJECUTOR
        self.vista = VistaTerminal(root, self)

        if self.auth.validar_credenciales():
            print("🔒 Seguridad: Credenciales de Binance cargadas y validadas.")
        else:
            print("⚠️ Alerta: No se encontró el archivo .env o faltan las credenciales.")

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
            self.modelo.iniciar_stream_precio(self.actualizar_precio_interfaz)
            
            decision_limpia = decision.replace(" ", "", 1).strip()
            self.dao.guardar_decision(self.modelo.precio_actual, self.modelo.rsi_actual, decision_limpia)

            
            # --- NUEVO: EJECUCIÓN DE ORDEN ---
            # Si el bot aprueba una compra o venta, mandamos la petición a Binance
            if "COMPRA APROBADA" in decision:
                print("\nEnviando orden de COMPRA a la Testnet...")
                exito_orden, mensaje = self.ejecutor.enviar_orden_mercado('BUY')
                print(mensaje)
                
            elif "VENTA APROBADA" in decision:
                print("\nEnviando orden de VENTA a la Testnet...")
                exito_orden, mensaje = self.ejecutor.enviar_orden_mercado('SELL')
                print(mensaje)

            else:
                # NUEVO: Nos avisa en consola si la operación se bloqueó
                print(f"\nMercado inestable. {decision.strip()}. No se enviarán órdenes.")

    def actualizar_precio_interfaz(self, precio_nuevo):
        self.vista.root.after(0, lambda: self.vista.lbl_precio.config(text=f"Precio Actual: ${precio_nuevo:,.2f}"))

    def iniciar_simulacion(self):
        self.vista.lbl_sim_resultado.config(text="Procesando 500 días de IA histórica...", foreground="#f3ba2f")
        self.vista.root.update()
        
        self.simulador = MotorBacktesting() 
        exito, capital, rendimiento, operaciones, win_rate = self.simulador.ejecutar_simulacion()
        self.vista.actualizar_simulacion(exito, capital, rendimiento, operaciones, win_rate)