from pydantic_settings import BaseSettings
from typing import Optional, ClassVar
import ssl
import os

class Settings(BaseSettings):
    """Configuración de la aplicación"""
    APP_NAME: str = "EFC Microservice"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    API_URL: str = ""  # Valor por defecto vacío, se carga desde .env
    API_TOKEN: str = ""  # Valor por defecto vacío, se carga desde .env 
    
    # Configuración de API externa
    SOAP_SERVICE_URL: str = "https://api.ejemplo.com"
    EXTERNAL_API_TIMEOUT: int = 30
    
    # SSL context como ClassVar para evitar que sea un field del modelo
    context: ClassVar[ssl.SSLContext] = ssl.create_default_context()
    
    # Configuración de reintentos y timeouts
    MAX_RETRIES: int = 3
    WAIT_TIME: int = 0
    VERIFY_SSL: bool = True
    TIMEOUT: int = 5  # Timeout por defecto para las peticiones HTTP

    # Configuración del servidor
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # Configuración de seguridad
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    model_config = {"env_file": ".env"}
    
    def __init__(self, **kwargs):

        super().__init__(**kwargs)

        
        # Configurar SSL context después de la inicialización
        if hasattr(self, 'context'):
            self.context.set_ciphers('DEFAULT:@SECLEVEL=1')


settings = Settings()
