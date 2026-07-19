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
        self.lbl_sim_resultado.pack(pady=10)
        self.lbl_sim_riesgo = ttk.Label(sim_frame, text="Sharpe: --- | Sortino: --- | Max Drawdown: ---", foreground="#9e9e9e")
        self.lbl_sim_riesgo.pack(pady=5)
        self.lbl_sim_benchmark = ttk.Label(sim_frame, text="vs Buy & Hold: ---", foreground="#9e9e9e")
        self.lbl_sim_benchmark.pack(pady=5)

        btn_simular = ttk.Button(main_frame, text="Simular Estrategia", style="Accion.TButton", command=self.controlador.iniciar_simulacion)
        btn_simular.pack(pady=5)

        selector_frame = ttk.Frame(main_frame)
        selector_frame.pack(pady=5)
        ttk.Label(selector_frame, text="Periodo a simular (días):", font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)
        self.periodo_var = tk.StringVar(value="500")
        combo_periodo = ttk.Combobox(selector_frame, textvariable=self.periodo_var,
                                      values=["250", "500", "750", "1000"], width=6, state="readonly")
        combo_periodo.pack(side=tk.LEFT)
        ttk.Label(selector_frame, text="(compara varios para ver si la estrategia es consistente, no solo suerte de un periodo)",
                  font=("Segoe UI", 9), foreground="#9e9e9e").pack(side=tk.LEFT, padx=5)

    def obtener_periodo_seleccionado(self):
        return int(self.periodo_var.get())

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

    def actualizar_simulacion(self, resultado):
        if resultado["exito"]:
            rendimiento = resultado["rendimiento_pct"]
            color = "#4caf50" if rendimiento > 0 else "#ff4c4c"

            resumen = (f"Operaciones realizadas: {resultado['operaciones']} "
                       f"({resultado['stops_activados']} por stop-loss) | "
                       f"Tasa de acierto: {resultado['win_rate']:.1f}%")
            resultado_txt = f"Capital Final: ${resultado['capital_final']:,.2f} USD ({rendimiento:+.2f}%)"

            self.lbl_sim_resumen.config(text=resumen)
            self.lbl_sim_resultado.config(text=resultado_txt, foreground=color)

            self.lbl_sim_riesgo.config(
                text=(f"Sharpe: {resultado['sharpe']} | Sortino: {resultado['sortino']} | "
                      f"Max Drawdown: {resultado['max_drawdown_pct']:.2f}%")
            )

            diferencia = rendimiento - resultado["buyhold_pct"]
            color_bench = "#4caf50" if diferencia > 0 else "#ff4c4c"
            veredicto = "le gana a" if diferencia > 0 else "pierde contra"
            self.lbl_sim_benchmark.config(
                text=(f"vs Buy & Hold ({resultado['buyhold_pct']:+.2f}%): la estrategia {veredicto} "
                      f"comprar-y-mantener por {diferencia:+.2f} pts"),
                foreground=color_bench
            )
        else:
            self.lbl_sim_resultado.config(text=f"Error en simulación: {resultado.get('error', 'desconocido')}", foreground="#ff4c4c")
            self.lbl_sim_riesgo.config(text="Sharpe: --- | Sortino: --- | Max Drawdown: ---")
            self.lbl_sim_benchmark.config(text="vs Buy & Hold: ---")