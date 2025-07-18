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

    async def get_pedimento_services(self, pedimento, service_type=3) -> List[Dict[str, Any]]:
        """
        Método para obtener la lista de servicios desde la API.
        """
        return await self._make_request_async('GET', f'customs/procesamientopedimentos/?pedimento={pedimento}&estado=1&servicio={service_type}')
    
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

    async def post_document(self, soap_response=None, organizacion: str = None, pedimento: str = None, file_name: str = None, document_type: int = 2, binary_content: bytes = None) -> Dict[str, Any]:
        """
        Método para enviar documentos (XML, PDF, etc.) a la API.
        
        Args:
            soap_response: Respuesta del servicio SOAP (para archivos XML)
            organizacion: UUID de la organización (requerido)
            pedimento: UUID del pedimento (requerido)
            file_name: Nombre del archivo con extensión (requerido)
            document_type: Tipo de documento
            binary_content: Contenido binario del archivo (para PDFs, etc.)
        """
        import datetime
        import tempfile
        import mimetypes
        
        if not soap_response and not binary_content:
            print("Error: Debe proporcionar soap_response o binary_content")
            return None
            
        if not file_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"documento_{timestamp}.bin"
        
        try:
            # Extraer extensión del nombre del archivo
            file_extension = os.path.splitext(file_name)[1].lstrip('.').lower()
            if not file_extension:
                file_extension = 'bin'  # Extensión por defecto
            
            # Determinar Content-Type basado en la extensión
            content_type_map = {
                'xml': 'application/xml',
                'pdf': 'application/pdf',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'zip': 'application/zip',
                'doc': 'application/msword',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'xls': 'application/vnd.ms-excel',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            
            content_type = content_type_map.get(file_extension, 'application/octet-stream')
            
            # Determinar modo de archivo y contenido
            if binary_content:
                # Para archivos binarios (PDFs, imágenes, etc.)
                file_mode = 'wb'
                temp_suffix = f'.{file_extension}'
                content = binary_content
                is_binary = True
            else:
                # Para archivos de texto (XML)
                file_mode = 'w'
                temp_suffix = f'.{file_extension}'
                is_binary = False
                
                # Obtener contenido de la respuesta SOAP
                if hasattr(soap_response, 'content'):
                    content = soap_response.content.decode('utf-8')
                elif hasattr(soap_response, 'text'):
                    content = soap_response.text
                else:
                    content = str(soap_response)
            
            # Crear archivo temporal con la extensión correcta
            encoding = None if is_binary else 'utf-8'
            with tempfile.NamedTemporaryFile(mode=file_mode, suffix=temp_suffix, delete=False, encoding=encoding) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            # Preparar headers para multipart/form-data (sin Content-Type)
            headers = {
                'Authorization': f'Token {settings.API_TOKEN}'
            }
            
            # Calcular tamaño del archivo
            file_size = os.path.getsize(temp_file_path)
            
            # Preparar datos del documento
            document_data = {
                'organizacion': organizacion,
                'pedimento': pedimento,
                'extension': file_extension,
                'document_type': document_type,
                'size': file_size
            }
            
            # Subir archivo
            url = f"{self.base_url}/record/documents/"
            
            # Usar httpx AsyncClient para la petición asíncrona
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                with open(temp_file_path, 'rb') as file:
                    files = {
                        'archivo': (file_name, file.read(), content_type)
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
            
            print(f"Documento {file_extension.upper()} enviado exitosamente: {file_name} (tamaño: {file_size} bytes)")
            return result
            
        except Exception as e:
            print(f"Error al enviar documento: {e}")
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

    async def get_edocs(self, pedimento: str) -> List[Dict[str, Any]]:
        """
        Método para obtener los documentos digitalizados de un pedimento.
        
        Args:
            pedimento: UUID del pedimento a consultar
        """
        return await self._make_request_async('GET', f'customs/edocuments/?pedimento={pedimento}')
    
    async def put_edocument(self, edocument_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método para actualizar un documento digitalizado en la API.
        
        Args:
            edocument_id: UUID del documento a actualizar
            data: Diccionario con los datos a actualizar
        """
        return await self._make_request_async('PUT', f'customs/edocuments/{edocument_id}/', data=data)

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