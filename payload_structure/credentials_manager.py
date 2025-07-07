from typing import Dict, Optional, List
from controllers.RESTController import APIController
from payload_structure.soap_models import CredencialesVUCEM, CredencialesSOAP

class CredentialsManager:
    """Gestor de credenciales VUCEM"""
    
    def __init__(self, api_controller: APIController):
        self.api_controller = api_controller
        self._credentials_cache: Dict[str, CredencialesVUCEM] = {}
    
    def get_credentials_by_user(self, importador: str) -> Optional[CredencialesVUCEM]:
        """
        Obtiene las credenciales de un importador específico
        
        Args:
            importador: Usuario/importador para obtener credenciales
            
        Returns:
            CredencialesVUCEM o None si no se encuentran
        """
        # Verificar cache primero
        if importador in self._credentials_cache:
            credentials = self._credentials_cache[importador]
            if credentials.is_active:
                return credentials
        
        # Obtener desde API
        try:
            response = self.api_controller.get_vucem_credentials(importador)
            # Validar respuesta antes de procesarla
            if not self.validate_response_data(response, importador):
                return None
            
            if response:
                # Manejar respuesta como lista (formato actual de la API)
                credentials_data = None
                
                if isinstance(response, list):
                    if len(response) == 0:
                        print(f"Lista de credenciales vacía para {importador}")
                        return None
                    
                    # La API devuelve una lista, tomar el primer elemento activo
                    for item in response:
                        if isinstance(item, dict) and item.get('is_active', False):
                            credentials_data = item
                            break
                    
                    # Si no hay activos, tomar el primero disponible
                    if not credentials_data:
                        try:
                            credentials_data = response[0]
                        except IndexError:
                            print(f"Error: Lista de credenciales está vacía para {importador}")
                            return None
                        
                elif isinstance(response, dict):
                    # Fallback: respuesta directa como diccionario
                    credentials_data = response
                else:
                    print(f"Formato de respuesta inesperado para {importador}: {type(response)}")
                    return None
                
                if credentials_data:
                    credentials = CredencialesVUCEM(**credentials_data)
                    # Guardar en cache si están activas
                    if credentials.is_active:
                        self._credentials_cache[importador] = credentials
                    return credentials
                else:
                    print(f"No se encontraron credenciales válidas para {importador}")
                    
        except Exception as e:
            print(f"Error al obtener credenciales para {importador}: {e}")
            if 'response' in locals():
                print(f"Tipo de respuesta: {type(response)}")
                print(f"Contenido: {response}")
        
        return None
    
    def get_soap_credentials(self, importador: str) -> Optional[CredencialesSOAP]:
        """
        Obtiene credenciales SOAP para un importador
        
        Args:
            importador: Usuario/importador para obtener credenciales
            
        Returns:
            CredencialesSOAP o None si no se encuentran
        """
        vucem_creds = self.get_credentials_by_user(importador)
        if vucem_creds:
            return vucem_creds.to_soap_credentials()
        return None
    
    def get_credentials_by_type(self, acuse_type: str = "cove", importador: str = None) -> List[CredencialesVUCEM]:
        """
        Obtiene credenciales filtradas por tipo de acuse
        
        Args:
            acuse_type: "cove" o "edocument"
            importador: Usuario específico (opcional)
            
        Returns:
            Lista de credenciales que soportan el tipo de acuse
        """
        if importador:
            # Obtener credenciales de un importador específico
            all_creds = self.get_active_credentials_for_user(importador)
        else:
            # Si no hay importador específico, usar cache disponible
            all_creds = [cred for cred in self._credentials_cache.values() if cred.is_active]
        
        # Filtrar por tipo de acuse
        filtered_creds = []
        for cred in all_creds:
            if acuse_type.lower() == "cove" and cred.acusecove:
                filtered_creds.append(cred)
            elif acuse_type.lower() == "edocument" and cred.acuseedocument:
                filtered_creds.append(cred)
        
        return filtered_creds
    
    def clear_cache(self):
        """Limpia el cache de credenciales"""
        self._credentials_cache.clear()
    
    def refresh_credentials(self, importador: str) -> Optional[CredencialesVUCEM]:
        """
        Fuerza la actualización de credenciales desde la API
        
        Args:
            importador: Usuario/importador para refrescar credenciales
            
        Returns:
            CredencialesVUCEM actualizadas o None
        """
        # Limpiar cache para este usuario
        if importador in self._credentials_cache:
            del self._credentials_cache[importador]
        
        # Obtener credenciales frescas
        return self.get_credentials_by_user(importador)
    
    def get_all_credentials_for_user(self, importador: str) -> List[CredencialesVUCEM]:
        """
        Obtiene todas las credenciales de un importador (puede tener múltiples)
        
        Args:
            importador: Usuario/importador para obtener credenciales
            
        Returns:
            Lista de CredencialesVUCEM
        """
        try:
            response = self.api_controller.get_vucem_credentials(importador)
            if response and isinstance(response, list):
                credentials_list = []
                for item in response:
                    if isinstance(item, dict):
                        try:
                            credentials = CredencialesVUCEM(**item)
                            credentials_list.append(credentials)
                        except Exception as e:
                            print(f"Error al procesar credencial: {e}")
                            continue
                return credentials_list
        except Exception as e:
            print(f"Error al obtener todas las credenciales para {importador}: {e}")
        
        return []
    
    def get_active_credentials_for_user(self, importador: str) -> List[CredencialesVUCEM]:
        """
        Obtiene solo las credenciales activas de un importador
        
        Args:
            importador: Usuario/importador para obtener credenciales
            
        Returns:
            Lista de CredencialesVUCEM activas
        """
        all_credentials = self.get_all_credentials_for_user(importador)
        return [cred for cred in all_credentials if cred.is_active]
    
    def debug_credentials(self, importador: str):
        """
        Método de debugging para mostrar información detallada de credenciales
        
        Args:
            importador: Usuario/importador para debuggear
        """
        print(f"\n=== DEBUG CREDENCIALES PARA {importador} ===")
        
        try:
            # Obtener respuesta cruda de la API
            response = self.api_controller.get_vucem_credentials(importador)
            print(f"Tipo de respuesta: {type(response)}")
            print(f"Contenido de respuesta: {response}")
            
            if isinstance(response, list):
                print(f"Cantidad de elementos en lista: {len(response)}")
                for i, item in enumerate(response):
                    print(f"  Elemento {i}: {type(item)}")
                    if isinstance(item, dict):
                        print(f"    - usuario: {item.get('usuario')}")
                        print(f"    - is_active: {item.get('is_active')}")
                        print(f"    - acusecove: {item.get('acusecove')}")
                        print(f"    - acuseedocument: {item.get('acuseedocument')}")
            
            # Intentar obtener credenciales procesadas
            creds = self.get_credentials_by_user(importador)
            if creds:
                print(f"Credenciales procesadas exitosamente:")
                print(f"  - Usuario: {creds.usuario}")
                print(f"  - Activo: {creds.is_active}")
                print(f"  - Patente: {creds.patente}")
            else:
                print("No se pudieron procesar las credenciales")
                
        except Exception as e:
            print(f"Error en debug: {e}")
        
        print("=== FIN DEBUG ===\n")
    
    def validate_response_data(self, response, importador: str) -> bool:
        """
        Valida que la respuesta de la API tenga el formato correcto
        
        Args:
            response: Respuesta de la API
            importador: Usuario para logging
            
        Returns:
            True si los datos son válidos, False en caso contrario
        """
        try:
            if response is None:
                print(f"Respuesta nula para {importador}")
                return False
            
            if isinstance(response, list):
                if len(response) == 0:
                    print(f"Lista de credenciales vacía para {importador}")
                    return False
                
                # Validar que todos los elementos de la lista sean diccionarios
                for i, item in enumerate(response):
                    if not isinstance(item, dict):
                        print(f"Elemento {i} no es un diccionario para {importador}: {type(item)}")
                        return False
                        
                return True
                
            elif isinstance(response, dict):
                return True
            else:
                print(f"Tipo de respuesta inesperado para {importador}: {type(response)}")
                return False
                
        except Exception as e:
            print(f"Error validando respuesta para {importador}: {e}")
            return False
