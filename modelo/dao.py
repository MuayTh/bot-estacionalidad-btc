import sqlite3
import datetime

class OperacionDAO:
    def __init__(self):
        self.nombre_bd = "auditoria_bot.db"
        self._inicializar_base_datos()

    def _inicializar_base_datos(self):
        # Se conecta y crea el archivo si no existe
        conexion = sqlite3.connect(self.nombre_bd)
        cursor = conexion.cursor()
        
        # Creamos la tabla con estructura SQL estándar
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registro_decisiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                precio REAL NOT NULL,
                rsi REAL NOT NULL,
                decision TEXT NOT NULL
            )
        ''')
        conexion.commit()
        conexion.close()

    def guardar_decision(self, precio, rsi, decision):
        try:
            conexion = sqlite3.connect(self.nombre_bd)
            cursor = conexion.cursor()
            
            fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute('''
                INSERT INTO registro_decisiones (fecha, precio, rsi, decision)
                VALUES (?, ?, ?, ?)
            ''', (fecha_actual, precio, rsi, decision))
            
            conexion.commit()
            conexion.close()
            return True
        except Exception as e:
            print(f"Error en BD: {e}")
            return False