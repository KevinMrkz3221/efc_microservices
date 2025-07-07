from fastapi import APIRouter
from core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    """Endpoint para verificar el estado del servicio"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }

@router.get("/")
async def root():
    """Endpoint raíz del microservicio"""
    return {
        "message": f"Bienvenido a {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs"
    }
