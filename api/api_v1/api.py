from fastapi import APIRouter
from api.api_v1.endpoints import health, pedimentos

api_router = APIRouter()

# Incluir routers de endpoints
api_router.include_router(health.router, tags=["health"])
api_router.include_router(pedimentos.router, tags=["pedimentos"])

