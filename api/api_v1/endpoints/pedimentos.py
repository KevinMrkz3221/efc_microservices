from fastapi import APIRouter, HTTPException
from schemas.pedimentoSchema import PedimentoRequest

router = APIRouter()


@router.post("/services/pedimento_completo")
async def get_pedimento_completo(request: PedimentoRequest):
    pass