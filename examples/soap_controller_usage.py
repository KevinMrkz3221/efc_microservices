"""
Ejemplo de uso de la instancia global del SOAPController

Este archivo muestra las mejores prácticas para usar una instancia global
del controlador SOAP en lugar de crear nuevas instancias en cada petición.
"""

from controllers.SOAPController import soap_controller
import asyncio
import logging

logger = logging.getLogger(__name__)

# ✅ CORRECTO: Usar instancia global
class PedimentoService:
    """
    Servicio que usa la instancia global del SOAPController
    """
    
    def __init__(self):
        # NO crear nueva instancia del controlador
        # self.soap_controller = SOAPController()  # ❌ INCORRECTO
        
        # Usar la instancia global
        self.controller = soap_controller  # ✅ CORRECTO
    
    def get_pedimento_data(self, pedimento_id: str, organizacion_id: str):
        """
        Obtener datos del pedimento usando la instancia global
        """
        soap_envelope = f"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <GetPedimento>
                    <pedimento_id>{pedimento_id}</pedimento_id>
                    <organizacion_id>{organizacion_id}</organizacion_id>
                </GetPedimento>
            </soap:Body>
        </soap:Envelope>
        """
        
        response = self.controller.make_request(
            endpoint="GetPedimento",
            data=soap_envelope,
            headers={'SOAPAction': 'GetPedimento'}
        )
        
        if response:
            return response.text
        return None

# ✅ CORRECTO: Usar directamente la instancia global
def get_pedimento_simple(pedimento_id: str):
    """
    Función que usa directamente la instancia global
    """
    soap_data = f"""
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <GetPedimentoSimple>
                <id>{pedimento_id}</id>
            </GetPedimentoSimple>
        </soap:Body>
    </soap:Envelope>
    """
    
    # Usar directamente la instancia global
    return soap_controller.make_request(
        endpoint="GetPedimentoSimple",
        data=soap_data
    )

# ✅ CORRECTO: En endpoints de FastAPI
async def endpoint_example(pedimento_id: str, organizacion_id: str):
    """
    Ejemplo de uso en endpoint de FastAPI
    """
    # Usar la instancia global directamente
    soap_data = f"""
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
        <soap:Body>
            <GetPedimentoCompleto>
                <pedimento_id>{pedimento_id}</pedimento_id>
                <organizacion_id>{organizacion_id}</organizacion_id>
            </GetPedimentoCompleto>
        </soap:Body>
    </soap:Envelope>
    """
    
    response = soap_controller.make_request(
        endpoint="GetPedimentoCompleto",
        data=soap_data,
        headers={'SOAPAction': 'GetPedimentoCompleto'}
    )
    
    if response:
        return {"status": "success", "data": response.text}
    else:
        return {"status": "error", "message": "Failed to get pedimento data"}

# ❌ INCORRECTO: Crear nueva instancia cada vez
def bad_example():
    """
    Ejemplo de lo que NO debes hacer
    """
    # ❌ MALO: Crear nueva instancia
    controller = SOAPController()
    
    # Esto desperdicia recursos y es ineficiente
    response = controller.make_request("endpoint", "data")
    
    # La instancia se destruye al salir de la función
    return response

# ✅ VENTAJAS DE LA INSTANCIA GLOBAL:

class VentajasInstanciaGlobal:
    """
    Documentación de las ventajas de usar instancia global
    """
    
    def performance_benefits(self):
        """
        Beneficios de performance:
        - Reutilización de conexiones HTTP
        - Menos overhead de creación/destrucción
        - Pool de conexiones persistente
        - Menos garbage collection
        """
        pass
    
    def resource_management(self):
        """
        Gestión de recursos:
        - Una sola configuración centralizada
        - Manejo consistente de timeouts
        - Logging centralizado
        - Mejor control de límites de conexión
        """
        pass
    
    def consistency_benefits(self):
        """
        Consistencia:
        - Misma configuración en toda la aplicación
        - Headers consistentes
        - Manejo uniforme de errores
        - Configuración desde variables de entorno
        """
        pass

# ✅ PATRÓN SINGLETON (Alternativa más explícita)
class SOAPControllerSingleton:
    """
    Implementación explícita del patrón Singleton
    """
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            # Inicializar solo una vez
            self.base_url = "https://api.ejemplo.com"
            self.timeout = 30
            self._initialized = True
            logger.info("SOAPController Singleton inicializado")
    
    def make_request(self, endpoint, data=None):
        # Implementación del método
        pass

# Ejemplo de uso con FastAPI y background tasks
async def background_task_example():
    """
    Ejemplo usando la instancia global en tareas de segundo plano
    """
    # La instancia global funciona perfectamente en tareas async
    response = soap_controller.make_request(
        endpoint="BackgroundProcess",
        data="<xml>background data</xml>"
    )
    
    if response:
        logger.info("Tarea de segundo plano completada")
    else:
        logger.error("Error en tarea de segundo plano")

if __name__ == "__main__":
    # Ejemplo de uso
    service = PedimentoService()
    result = service.get_pedimento_data("PED123", "ORG456")
    print(f"Resultado: {result}")
