from binance.client import Client
from binance.exceptions import BinanceAPIException
from modelo.autenticacion import GestorCredenciales

class GestorOrdenes:
    def __init__(self):
        # Instanciamos tu bóveda de seguridad
        self.auth = GestorCredenciales()
        self.cliente = None
        
        if self.auth.validar_credenciales():
            # Conectamos a Binance. testnet=True es vital para no usar dinero real.
            self.cliente = Client(self.auth.api_key, self.auth.api_secret, testnet=True)

    def enviar_orden_mercado(self, tipo_orden, cantidad=0.001):
        if not self.cliente:
            return False, "⚠️ Cliente Binance no inicializado (revisa tus claves)."

        try:
            # tipo_orden debe ser la cadena 'BUY' o 'SELL'
            respuesta = self.cliente.create_order(
                symbol='BTCUSDT',
                side=tipo_orden,
                type='MARKET',
                quantity=cantidad
            )
            return True, f"✅ Orden ejecutada con éxito: {tipo_orden} {cantidad} BTC"
            
        except BinanceAPIException as e:
            # Binance detectará que nuestras claves (del archivo .env) son inventadas
            return False, f"❌ Rechazado por Binance: {e.message}"
        except Exception as e:
            return False, f"❌ Error interno de conexión: {e}"