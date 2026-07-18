import tkinter as tk
from tkinter import ttk
import datetime

class VistaTerminal:
    def __init__(self, root, controlador):
        self.root = root
        self.controlador = controlador
        self.root.title("Terminal Cuantitativa - BTC Estacionalidad")
        self.root.geometry("1100x850") # Ventana un poco más alta
        self.root.configure(bg="#1e1e1e")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TLabel", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 12))
        style.configure("Titulo.TLabel", font=("Segoe UI", 24, "bold"), foreground="#f3ba2f")
        style.configure("Metrica.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Decision.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Accion.TButton", font=("Segoe UI", 12, "bold"), padding=10)

        self.crear_widgets()

    def crear_widgets(self):
        main_frame = ttk.Frame(self.root, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Panel de Análisis Cuantitativo", style="Titulo.TLabel").pack(pady=(0, 10))

        # PANELES SUPERIORES (IA y Estacionalidad)
        paneles_frame = ttk.Frame(main_frame)
        paneles_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        ia_frame = ttk.LabelFrame(paneles_frame, text=" Motor de IA (Regresión) ", padding="20 20 20 20")
        ia_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.lbl_precio = ttk.Label(ia_frame, text="Precio Actual: ---")
        self.lbl_precio.pack(pady=10)
        self.lbl_proyeccion = ttk.Label(ia_frame, text="Proyección Mañana: ---")
        self.lbl_proyeccion.pack(pady=10)
        self.lbl_tendencia_ia = ttk.Label(ia_frame, text="Señal IA: ---", style="Metrica.TLabel")
        self.lbl_tendencia_ia.pack(pady=10)
        self.lbl_confianza = ttk.Label(ia_frame, text="Ajuste del modelo (R²): ---", foreground="#9e9e9e")
        self.lbl_confianza.pack(pady=10)

        est_frame = ttk.LabelFrame(paneles_frame, text=" Filtro Estacional ", padding="20 20 20 20")
        est_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        self.lbl_mes = ttk.Label(est_frame, text=f"Mes Actual: {datetime.datetime.now().strftime('%B')}")
        self.lbl_mes.pack(pady=10)
        self.lbl_probabilidad = ttk.Label(est_frame, text="Win Rate Histórico: ---")
        self.lbl_probabilidad.pack(pady=10)
        self.lbl_muestra = ttk.Label(est_frame, text="Muestra: ---", foreground="#9e9e9e")
        self.lbl_muestra.pack(pady=2)
        self.lbl_riesgo = ttk.Label(est_frame, text="Nivel de Riesgo: ---", style="Metrica.TLabel")
        self.lbl_riesgo.pack(pady=20)

        # PANEL DECISIÓN (Centro)
        decision_frame = ttk.LabelFrame(main_frame, text=" DECISIÓN EN TIEMPO REAL ", padding="15 15 15 15")
        decision_frame.pack(fill=tk.X, pady=10)
        self.lbl_decision = ttk.Label(decision_frame, text="ESPERANDO DATOS...", style="Decision.TLabel", foreground="#ffffff")
        self.lbl_decision.pack()

        btn_conectar = ttk.Button(main_frame, text="Ejecutar Análisis Maestro", style="Accion.TButton", command=self.controlador.iniciar_sistema)
        btn_conectar.pack(pady=10)

        # NUEVO PANEL: BACKTESTING (Inferior)
        sim_frame = ttk.LabelFrame(main_frame, text=" Laboratorio de Backtesting (Simulador) ", padding="15 15 15 15")
        sim_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.lbl_sim_resumen = ttk.Label(sim_frame, text="Capital Inicial: $1,000.00 USD", font=("Segoe UI", 12))
        self.lbl_sim_resumen.pack(pady=5)
        self.lbl_sim_resultado = ttk.Label(sim_frame, text="Ejecuta la simulación para probar el algoritmo.", style="Metrica.TLabel")
        self.lbl_sim_resultado.pack(pady=15)

        btn_simular = ttk.Button(main_frame, text="Simular Estrategia (Últimos 500 días)", style="Accion.TButton", command=self.controlador.iniciar_simulacion)
        btn_simular.pack(pady=5)

    def actualizar_pantalla(self, exito, modelo, decision_final, color_decision):
        if exito:
            self.lbl_precio.config(text=f"Precio Actual: ${modelo.precio_actual:,.2f}")
            self.lbl_proyeccion.config(text=f"Proyección Mañana: ${modelo.prediccion_mañana:,.2f}")
            color_ia = "#4caf50" if "ALCISTA" in modelo.tendencia_ia else "#ff4c4c"
            self.lbl_tendencia_ia.config(text=f"Señal IA: {modelo.tendencia_ia}", foreground=color_ia)

            confianza = getattr(modelo, 'confianza_modelo', None)
            if confianza is not None:
                self.lbl_confianza.config(text=f"Ajuste del modelo (R²): {confianza:.2f} (solo referencial, no garantiza acierto futuro)")

            muestra = getattr(modelo, 'muestra_mes_actual', 0)
            self.lbl_muestra.config(text=f"Muestra: {muestra} años observados")

            self.lbl_probabilidad.config(text=f"Win Rate Histórico: {modelo.probabilidad_mes}%")
            color_riesgo = "#4caf50" if "Favorable" in modelo.riesgo_estacional else ("#ff4c4c" if "Peligroso" in modelo.riesgo_estacional else "#f3ba2f")
            self.lbl_riesgo.config(text=f"Nivel de Riesgo: {modelo.riesgo_estacional}", foreground=color_riesgo)
            self.lbl_decision.config(text=decision_final, foreground=color_decision)

    def actualizar_simulacion(self, exito, capital, rendimiento, operaciones, win_rate):
        if exito:
            color = "#4caf50" if rendimiento > 0 else "#ff4c4c"
            resumen = f"Operaciones realizadas: {operaciones} | Tasa de acierto: {win_rate:.1f}%"
            resultado = f"Capital Final: ${capital:,.2f} USD ({rendimiento:+.2f}%)"
            
            self.lbl_sim_resumen.config(text=resumen)
            self.lbl_sim_resultado.config(text=resultado, foreground=color)
        else:
            self.lbl_sim_resultado.config(text=f"Error en simulación: {capital}", foreground="#ff4c4c")