from pydantic_settings import BaseSettings
from typing import Optional
import ssl
class Settings(BaseSettings):
    """Configuración de la aplicación"""
    app_name: str = "EFC Microservice"
    app_version: str = "1.0.0"
    debug: bool = False

    API_URL: str = "http://localhost:8000/api/v1"
    
    # Configuración de API externa
    SOAP_SERVICE_URL: str = "https://api.ejemplo.com"
    EXTERNAL_API_TIMEOUT: int = 30
    
    context = ssl.create_default_context()
    context.set_ciphers('DEFAULT:@SECLEVEL=1')
    # Configuración de reintentos y timeouts
    MAX_RETRIES: int = 3
    WAIT_TIME: int = 0
    VERIFY_SSL: bool = True

    
    # Configuración del servidor
    host: str = "0.0.0.0"
    port: int = 8001
    
    
    # Configuración de seguridad
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 306
    
    class Config:
        env_file = ".env"


settings = Settings()
