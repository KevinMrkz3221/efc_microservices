from fastapi import APIRouter, HTTPException
from schemas.pedimentoSchema import PedimentoRequest
from schemas.serviceSchema import ServiceBaseSchema
import asyncio
import logging
from controllers.RESTController import rest_controller
from controllers.SOAPController import soap_controller
from utils.peticiones import get_soap_pedimento_completo
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/services/pedimento_completo")
async def get_pedimento_completo(request: ServiceBaseSchema):
    try:
        logger.info(f"Procesando pedimento completo")
        
        # Usar model_dump() en lugar de dict() para evitar problemas con UUID
        request_data = request.model_dump()
        logger.info(f"Request data: {request_data}")
        
        # Se crea el servicio para el pedimendo (Descarga de pedimento Completo)
        logger.info(f"Creando servicio de pedimento completo...{request_data['pedimento']}")
        response_service = await rest_controller.post_pedimento_service(request_data)
        logger.info(f"Respuesta recibida: {response_service}")
        
        # Si no se crea el servicio manda error 
        if response_service is None:
            logger.error("La respuesta del servicio es None")
            raise HTTPException(status_code=500, detail="Error al procesar el servicio de pedimento")

        if response_service:
            request_data['estado'] = 2
            response_put_service = await rest_controller.put_pedimento_service(response_service['id'], request_data)
            response_credentials = await rest_controller.get_vucem_credentials(response_service['pedimento']['contribuyente'])
            
            if response_put_service and response_credentials:
                logger.info("Credenciales obtenidas exitosamente")

                # Procesar petición SOAP para obtener pedimento completo
                get_pedimento_completo_response = await get_soap_pedimento_completo(
                    credenciales=response_credentials[0],
                    response_service=response_service,
                    soap_controller=soap_controller
                )

                # Intentar actualizar el pedimento, pero manejar si no existe
                try:
                    pedimento_response = await rest_controller.put_pedimento(
                        response_service['pedimento']['id'], 
                        get_pedimento_completo_response['xml_content']
                    )
                    logger.info(f"Pedimento actualizado exitosamente: {pedimento_response}")
                except Exception as e:
                    logger.warning(f"No se pudo actualizar el pedimento: {e}")
                    # Continuar con el proceso aunque no se pueda actualizar el pedimento
                
                service_finished = await rest_controller.put_pedimento_service(
                    service_id=response_service['id'],
                    data={
                        "estado": 3,  # Estado finalizado
                        "pedimento": response_service['pedimento']['id'],
                        "organizacion": response_service['organizacion'],
                    }
                )
                
                get_pedimento_completo_response['servicio'] = response_service['id']
                # Retornar la respuesta completa del procesamiento
                return JSONResponse(
                    content=get_pedimento_completo_response,
                    status_code=200
                )
            else:
                service_finished = await rest_controller.put_pedimento_service(
                    service_id=response_service['id'],
                    data={
                        "estado": 4,  # Estado finalizado
                        "pedimento": response_service['pedimento']['id'],
                        "organizacion": response_service['organizacion'],
                    }
                )
                raise HTTPException(status_code=500, detail="Error al actualizar el servicio de pedimento o obtener credenciales")

        else:
            service_finished = await rest_controller.put_pedimento_service(
                service_id=response_service['id'],
                data={
                    "estado": 4,  # Estado finalizado
                    "pedimento": response_service['pedimento']['id'],
                    "organizacion": response_service['organizacion'],
                }
            )
            raise HTTPException(status_code=500, detail="No se pudo crear el servicio de pedimento")
            
    except Exception as e:
        logger.error(f"Error en get_pedimento_completo: {e}")
        logger.error(f"Tipo de error: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/pedimentos/estado_pedimento")
async def get_estado_pedimento(request: PedimentoRequest):
    pass

@router.post("/pedimentos/remesas")
async def get_remesas(request: PedimentoRequest):
    pass

@router.post("/pedimentos/coves")
async def get_cove(request: PedimentoRequest):
    pass

@router.post("/pedimentos/edocument")
async def get_edocument(request: PedimentoRequest):
    pass
