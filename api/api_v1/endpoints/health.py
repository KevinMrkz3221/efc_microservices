from fastapi import APIRouter
from core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    """Endpoint para verificar el estado del servicio"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

@router.get("/")
async def root():
    """Endpoint raíz del microservicio"""
    return {
        "message": f"Bienvenido a {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }
