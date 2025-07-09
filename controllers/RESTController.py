import requests
import asyncio
import logging
from typing import List, Dict, Any
import os
import httpx
from core.config import settings 

logger = logging.getLogger(__name__) 

class APIController:
    """
    Controlador para manejar las peticiones a la API.
    """

    def __init__(self):
        self.base_url = settings.API_URL # URL base de la API
    
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {settings.API_TOKEN}'  # Token de autenticación
        }
        self.timeout = 5  # Timeout para las peticiones a la API

    def _make_request(self, method, endpoint, data=None):
        """
        Método para hacer peticiones a la API.
        """

        url = f"{self.base_url}/{endpoint}"
        try:

            response = requests.request(method, url, json=data, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()  # Lanza un error si la respuesta no es 200
            result = response.json()
            return result  # Retorna el JSON de la respuesta
        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                print(f"Status code del error: {e.response.status_code}")
                print(f"Contenido del error: {e.response.text}")
            return None

    def get_pedimento_services(self, page, service_type=3) -> List[Dict[str, Any]]:
        """
        Método para obtener la lista de servicios desde la API.
        """
        return self._make_request('GET', f'customs/procesamientopedimentos/?page={page}&page_size=40&estado=1&servicio={service_type}')
    
    async def get_pedimento(self, pedimento_id: str) -> Dict[str, Any]:
        """
        Método para obtener un pedimento específico desde la API.
        
        Args:
            pedimento: UUID del pedimento a consultar
        """
        return self._make_request('GET', f'customs/pedimentos/{pedimento_id}/')

    async def get_vucem_credentials(self, importador) -> Dict[str, Any]:
        """
        Método para obtener las credenciales de VUCEM desde la API.
        """
        return await self._make_request_async('GET', f'vucem/vucem/?usuario={importador}')
    
    async def post_pedimento_service(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método para crear un nuevo servicio de pedimento en la API.
        
        Args:
            data: Diccionario con los datos del servicio a crear
        """
        return await self._make_request_async('POST', 'customs/procesamientopedimentos/', data=data)
    
    async def put_pedimento_service(self, service_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método para actualizar un servicio de pedimento en la API.
        """
        return await self._make_request_async('PUT', f'customs/procesamientopedimentos/{service_id}/', data=data)

    async def put_pedimento(self, pedimento_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método para actualizar un pedimento en la API.
        """
        return await self._make_request_async('PUT', f'customs/pedimentos/{pedimento_id}/', data=data)

    async def post_document(self, soap_response, organizacion: str, pedimento: str, file_name: str = None) -> Dict[str, Any]:
        """
        Método para enviar una respuesta SOAP como documento archivo a la API.
        
        Args:
            soap_response: Respuesta del servicio SOAP
            organizacion: UUID de la organización (requerido)
            pedimento: UUID del pedimento (requerido)
            file_name: Nombre del archivo (opcional, se genera automáticamente)
        """
        import datetime
        import tempfile
        
        if not soap_response:
            print("Error: No hay respuesta SOAP para enviar")
            return None
        
        try:
            # Generar nombre de archivo si no se especifica
            if not file_name:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = f"pedimento_{pedimento}.xml"
            
            # Asegurar que termine en .xml
            if not file_name.endswith('.xml'):
                file_name += '.xml'
            
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as temp_file:
                # Obtener contenido de la respuesta SOAP
                if hasattr(soap_response, 'content'):
                    content = soap_response.content.decode('utf-8')
                elif hasattr(soap_response, 'text'):
                    content = soap_response.text
                else:
                    content = str(soap_response)
                
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            # Preparar headers para multipart/form-data (sin Content-Type)
            headers = {
                'Authorization': f'Token {settings.API_TOKEN}'
            }
            
            # Calcular tamaño del archivo
            file_size = os.path.getsize(temp_file_path)
            print(temp_file_path)
            # Preparar datos del documento (estos van en el body como form-data)
            document_data = {
                'organizacion': organizacion,
                'pedimento': pedimento,
                'extension': 'xml',  # Asumimos que es XML
                'document_type': 2,
                'size': file_size
            }
            
            # Subir archivo
            url = f"{self.base_url}/record/documents/"
            
            # Usar httpx AsyncClient para la petición asíncrona
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                with open(temp_file_path, 'rb') as file:
                    files = {
                        'archivo': (file_name, file.read(), 'application/xml')
                    }
                    
                    response = await client.post(
                        url,
                        data=document_data,  # Datos van como form-data
                        files=files,         # Archivo va como multipart
                        headers=headers
                    )
            
            # Limpiar archivo temporal
            os.unlink(temp_file_path)
            
            response.raise_for_status()
            result = response.json()
            
            print(f"Documento XML enviado exitosamente: {file_name} (tamaño: {file_size} bytes)")
            return result
            
        except Exception as e:
            print(f"Error al enviar documento SOAP: {e}")
            # Limpiar archivo temporal en caso de error
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            return None

    async def post_edocument(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método para enviar un documento digitalizado a la API.
        
        Args:
            data: Diccionario con los datos del documento a enviar
        """
        return await self._make_request_async('POST', 'customs/edocuments/', data=data)

    async def _make_request_async(self, method: str, endpoint: str, data=None):
        """
        Método asíncrono para hacer peticiones a la API usando httpx.
        """
        
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Haciendo petición {method} a {url}")
                
                if method.upper() == 'GET':
                    response = await client.get(url, headers=self.headers)
                elif method.upper() == 'POST':
                    response = await client.post(url, json=data, headers=self.headers)
                elif method.upper() == 'PUT':
                    response = await client.put(url, json=data, headers=self.headers)
                elif method.upper() == 'DELETE':
                    response = await client.delete(url, headers=self.headers)
                else:
                    raise ValueError(f"Método HTTP no soportado: {method}")

                response.raise_for_status()
                logger.info(f"Respuesta exitosa: {response.status_code}")
                
                result = response.json() if response.content else {}
                return result
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout en petición a {url}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Error HTTP {e.response.status_code} en {url}: {e}")

            return None
        except Exception as e:
            logger.error(f"Error inesperado en petición a {url}: {e}")
            import traceback
            return None


rest_controller = APIController()  # Instancia global del controlador REST