import os
from dotenv import load_dotenv

class GestorCredenciales:
    def __init__(self):
        # Carga las variables del archivo .env de forma segura en memoria
        load_dotenv()
        
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")

    def validar_credenciales(self):
        # Verifica que ambas claves existan y no estén vacías
        if self.api_key and self.api_secret:
            return True
        return False