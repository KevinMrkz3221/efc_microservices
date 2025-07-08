from core.config import settings 
from dataclasses import dataclass
import requests
import httpx
import datetime
import time

class SOAPController:
    """
    Controlador para manejar las peticiones SOAP.
    """

    def __init__(self):
        self.base_url = settings.SOAP_SERVICE_URL
        self.timeout = settings.TIMEOUT  # Timeout por default

    def make_request(self, endpoint, data=None, headers=None, max_retries=5):
        intento = 0
        while intento < settings.MAX_RETRIES:
            try:
                with httpx.Client(verify=settings.VERIFY_SSL, timeout=self.timeout) as client:
                    content = data.encode('utf-8') if data else None
                    response = client.post(
                        f"{self.base_url}/{endpoint}",
                        content=content,
                        headers=headers
                    )
                    response.raise_for_status()
                    return response  # ✅ éxito
            except Exception as e:
                intento += 1
                wait_time = 0
                print(f"[{endpoint}] Error intento {intento}: {e}. Reintentando en {settings.WAIT_TIME}s...")
                time.sleep(settings.WAIT_TIME)

        print(f"[{endpoint}] Fallo tras {settings.MAX_RETRIES} intentos.")
        return None

    async def make_request_async(self, endpoint, data=None, headers=None, max_retries=5):
        """
        Método asíncrono para hacer peticiones SOAP sin bloquear el event loop
        
        Args:
            endpoint: El endpoint al que se va a hacer la petición
            data: Los datos a enviar en la petición
            headers: Los headers HTTP a incluir en la petición
            max_retries: Número máximo de reintentos en caso de fallo
            
        Returns:
            La respuesta de la petición, o None si falla tras los reintentos
        """
        import asyncio
        intento = 0
        while intento < settings.MAX_RETRIES:
            try:
                async with httpx.AsyncClient(verify=settings.context, timeout=self.timeout) as client:
                    content = data.encode('utf-8') if data else None
                    response = await client.post(
                        f"{self.base_url}/{endpoint}",
                        content=content,
                        headers=headers
                    )
                    response.raise_for_status()
                    return response  # ✅ éxito
            except Exception as e:
                intento += 1
                print(f"[{endpoint}] Error intento {intento}: {e}. Reintentando en {settings.WAIT_TIME}s...")
                if intento < settings.MAX_RETRIES:
                    await asyncio.sleep(settings.WAIT_TIME)  # ASYNC SLEEP!

        print(f"[{endpoint}] Fallo tras {settings.MAX_RETRIES} intentos.")
        return None

    def generate_pedimento_completo_template(self, username: str, password: str, aduana: str, patente: str, pedimento: str) -> str:
        """
        Genera el template SOAP para consultar pedimento completo
        
        Args:
            username: Usuario de VUCEM
            password: Contraseña de VUCEM  
            aduana: Código de aduana
            patente: Número de patente
            pedimento: Número de pedimento
            
        Returns:
            str: Template SOAP XML completo
        """
        soap_template = f'''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
   xmlns:con="http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/consultarpedimentocompleto"
   xmlns:com="http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/comunes">
   <soapenv:Header>
      <wsse:Security soapenv:mustUnderstand="1"
         xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
         <wsse:UsernameToken>
            <wsse:Username>{username}</wsse:Username>
            <wsse:Password
               Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{password}</wsse:Password>
         </wsse:UsernameToken>
      </wsse:Security>
   </soapenv:Header>
   <soapenv:Body>
      <con:consultarPedimentoCompletoPeticion>
         <con:peticion>
            <com:aduana>{aduana}</com:aduana>
            <com:patente>{patente}</com:patente>
            <com:pedimento>{pedimento}</com:pedimento>
         </con:peticion>
      </con:consultarPedimentoCompletoPeticion>
   </soapenv:Body>
</soapenv:Envelope>'''
        
        return soap_template


soap_controller = SOAPController()  # Instancia global del controlador SOAP