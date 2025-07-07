from fastapi import FastAPI
from core.config import settings
from api.api_v1.api import api_router

def create_application() -> FastAPI:
    """Función factory para crear la aplicación FastAPI"""
    application = FastAPI(
        title=settings.app_name,
        description="EFC Microservice - Un microservicio profesional por AduanaSoft",
        version=settings.app_version,
        debug=settings.debug,
    )
    

    # Incluir el router principal de la API
    application.include_router(api_router, prefix="/api/v1")
    
    return application

app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
