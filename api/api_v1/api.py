from fastapi import APIRouter
from api.api_v1.endpoints import health, pedimentos, services
# En Python, no se pueden usar llaves {} para importar múltiples módulos.
# Debes usar paréntesis () para hacer importaciones multilínea.
from api.api_v1.endpoints import (
    health,
    pedimentos,
    services
)

api_router = APIRouter()

# Incluir routers de endpoints
api_router.include_router(health.router, tags=["health"])
api_router.include_router(pedimentos.router, tags=["pedimentos"])

