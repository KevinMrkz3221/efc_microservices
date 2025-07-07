from fastapi import APIRouter, HTTPException
from schemas.pedimentoSchema import PedimentoRequest
from services.pedimento_service import disparar_proceso_pedimento_completo

router = APIRouter()


@router.post("/services/pedimento_completo")
async def get_pedimento_completo(request: PedimentoRequest):
    """
    Obtener pedimento completo por ID de pedimento y organización
    
    Este endpoint dispara un proceso en segundo plano y retorna inmediatamente
    sin esperar a que el proceso termine.
    """
    
    # Disparar proceso en segundo plano SIN await
    resultado = await disparar_proceso_pedimento_completo(
        request.pedimento_id, 
        request.organizacion_id
    )
    
    return resultado