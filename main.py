import tkinter as tk
import ctypes
from controlador.gestor import ControladorTerminal

if __name__ == "__main__":
    # Forzar renderizado nítido en pantallas de alta resolución
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()
    app = ControladorTerminal(root)
    root.mainloop()