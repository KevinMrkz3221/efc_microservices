from fastapi import APIRouter, HTTPException
from schemas.pedimentoSchema import PedimentoRequest
from schemas.serviceSchema import ServiceBaseSchema, ServiceRemesaSchema
import asyncio
import logging
import traceback
from controllers.RESTController import rest_controller
from controllers.SOAPController import soap_controller
from utils.peticiones import get_soap_pedimento_completo, get_soap_remesas, get_soap_partidas
from fastapi.responses import JSONResponse
from core.config import settings

# Estados del servicio
ESTADO_CREADO = 1
ESTADO_EN_PROCESO = 2  
ESTADO_FINALIZADO = 3
ESTADO_ERROR = 4

router = APIRouter()
logger = logging.getLogger(__name__)

async def _post_edocuments(response_service: dict, identificadores_ed: list):
    """
    Helper function para enviar documentos digitalizados a la API.
    
    Args:
        response_service: Diccionario con datos del servicio
        identificadores_ed: Lista de identificadores ED a enviar
    """
    responses = []
    
    for identificador in identificadores_ed:
        # Preparar datos del documento
        document_data = {
            'clave': identificador['clave'],
            'descripcion': identificador['descripcion'],
            'numero_edocument': identificador['complemento1'],
            'organizacion': response_service['organizacion'],
            'pedimento': response_service['pedimento']['id']
        }

        try:
            response = await rest_controller.post_edocument(document_data)
            if response is None:
                logger.warning(f"No se pudo enviar el documento {identificador['complemento1']}")
                continue
            responses.append(response)
            logger.info(f"Documento {identificador['complemento1']} enviado exitosamente")
        except Exception as e:
            logger.error(f"Error al enviar el documento {identificador['complemento1']}: {e}")
            continue
    
    if not responses:
        raise HTTPException(status_code=500, detail="No se pudo enviar ningún documento digitalizado")
    
    return responses

async def _update_service_status(service_id: int, estado: int, response_service: dict):
    """
    Helper function para actualizar el estado del servicio
    
    Args:
        service_id: ID del servicio
        estado: Nuevo estado (3=finalizado, 4=error)
        response_service: Datos del servicio
    """
    try:
        await rest_controller.put_pedimento_service(
            service_id=service_id,
            data={
                "estado": estado,
                "pedimento": response_service['pedimento']['id'],
                "organizacion": response_service['organizacion'],
            }
        )
        logger.info(f"Estado del servicio actualizado a {estado}")
    except Exception as e:
        logger.error(f"Error al actualizar estado del servicio: {e}")

@router.post("/services/pedimento_completo")
async def get_pedimento_completo(request: ServiceBaseSchema):
    response_service = None
    try:
        logger.info(f"Procesando pedimento completo")
        
        # Usar model_dump() en lugar de dict() para evitar problemas con UUID
        request_data = request.model_dump()
        logger.info(f"Request data: {request_data}")
        
        # Validar datos de entrada
        if not request_data.get('pedimento'):
            raise HTTPException(status_code=400, detail="ID del pedimento es requerido")
        if not request_data.get('organizacion'):
            raise HTTPException(status_code=400, detail="ID de la organización es requerido")
        
        # Se crea el servicio para el pedimento (Descarga de pedimento Completo)
        logger.info(f"Creando servicio de pedimento completo...{request_data['pedimento']}")
        try:
            response_service = await rest_controller.post_pedimento_service(request_data)
            logger.info(f"Respuesta recibida: {response_service}")
        except Exception as e:
            logger.error(f"Error al crear servicio: {e}")
            raise HTTPException(status_code=500, detail="Error al crear el servicio de pedimento")
        
        # Si no se crea el servicio manda error 
        if response_service is None:
            logger.error("La respuesta del servicio es None")
            raise HTTPException(status_code=500, detail="Error al procesar el servicio de pedimento")

        # Actualizar estado a "En proceso"
        request_data['estado'] = ESTADO_EN_PROCESO
        try:
            response_put_service = await rest_controller.put_pedimento_service(response_service['id'], request_data)
        except Exception as e:
            logger.error(f"Error al actualizar estado del servicio: {e}")
            await _update_service_status(response_service['id'], ESTADO_ERROR, response_service)
            raise HTTPException(status_code=500, detail="Error al actualizar estado del servicio")
        
        # Obtener credenciales VUCEM
        try:
            response_credentials = await rest_controller.get_vucem_credentials(
                response_service['pedimento']['contribuyente']
            )
        except Exception as e:
            logger.error(f"Error al obtener credenciales VUCEM: {e}")
            await _update_service_status(response_service['id'], ESTADO_ERROR, response_service)
            raise HTTPException(status_code=500, detail="Error al obtener credenciales VUCEM")
        
        if not response_put_service or not response_credentials:
            await _update_service_status(response_service['id'], ESTADO_ERROR, response_service)
            raise HTTPException(status_code=500, detail="Error al actualizar el servicio de pedimento o obtener credenciales")

        logger.info("Credenciales obtenidas exitosamente")

        # Procesar petición SOAP para obtener pedimento completo
        try:
            get_pedimento_completo_response = await get_soap_pedimento_completo(
                credenciales=response_credentials[0],
                response_service=response_service,
                soap_controller=soap_controller
            )
        except Exception as e:
            logger.error(f"Error en petición SOAP: {e}")
            await _update_service_status(response_service['id'], ESTADO_ERROR, response_service)
            raise HTTPException(status_code=500, detail="Error en la petición SOAP al servicio VUCEM")

        # Intentar actualizar el pedimento, pero manejar si no existe
        try:
            # Excluir 'identificadores_ed' de xml_content antes de enviarlo
            xml_content = get_pedimento_completo_response.get('xml_content', {})
            if 'identificadores_ed' in xml_content:
                xml_content = {k: v for k, v in xml_content.items() if k != 'identificadores_ed'}

            pedimento_response = await rest_controller.put_pedimento(
                response_service['pedimento']['id'],
                xml_content
            )
            logger.info(f"Pedimento actualizado exitosamente: {pedimento_response}")
        except Exception as e:
            logger.warning(f"No se pudo actualizar el pedimento: {e}")
            # Continuar con el proceso aunque no se pueda actualizar el pedimento
        
        # Finalizar servicio exitosamente
        await _update_service_status(response_service['id'], ESTADO_FINALIZADO, response_service)
        
        get_pedimento_completo_response['servicio'] = response_service['id']

        # Procesar e-documents (documentos digitalizados) si existen
        try:
            identificadores_ed = get_pedimento_completo_response.get('xml_content', []).get('identificadores_ed', [])
            if identificadores_ed:
                logger.info(f"Procesando {len(identificadores_ed)} documentos digitalizados...")
                edocuments = await _post_edocuments(
                    response_service=response_service,
                    identificadores_ed=identificadores_ed
                )
                get_pedimento_completo_response['edocuments'] = edocuments
                logger.info(f"Se enviaron exitosamente {len(edocuments)} documentos digitalizados")
            else:
                logger.info("No se encontraron documentos digitalizados (identificadores ED)")
                get_pedimento_completo_response['edocuments'] = []
        except Exception as e:
            logger.error(f"Error al procesar documentos digitalizados: {e}")
            # No fallar todo el proceso por error en e-documents
            get_pedimento_completo_response['edocuments'] = []
            get_pedimento_completo_response['edocuments_error'] = str(e)
        # Crea servicios para remesas, estado del pedimento, coves y edocument
        try:
            new_service = {
                "pedimento": response_service['pedimento']['id'],
                "organizacion": response_service['organizacion'],
                "estado": ESTADO_CREADO,
                "tipo_procesamiento": 2,
                "servicio": 1
            }
            response_service_1 = await rest_controller.post_pedimento_service(new_service)
            new_service['servicio'] = 4
            response_service_4 = await rest_controller.post_pedimento_service(new_service)
            new_service['servicio'] = 5
            response_service_5 = await rest_controller.post_pedimento_service(new_service)
            new_service['servicio'] = 6
            response_service_6 = await rest_controller.post_pedimento_service(new_service)
            new_service['servicio'] = 7
            response_service_7 = await rest_controller.post_pedimento_service(new_service)
            get_pedimento_completo_response['servicios_adicionales'] = {
                "servicio_1": response_service_1['id'],
                "servicio_4": response_service_4['id'],
                "servicio_5": response_service_5['id'],
                "servicio_6": response_service_6['id'],
                "servicio_7": response_service_7['id']
            }
            logger.info("Servicios adicionales creados exitosamente")
        except Exception as e:
            logger.error(f"Error al crear servicios adicionales: {e}")
            # No fallar todo el proceso por error en servicios adicionales
            get_pedimento_completo_response['servicios_adicionales_error'] = str(e)
        return JSONResponse(
            content=get_pedimento_completo_response,
            status_code=200
        )
            
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en get_pedimento_completo: {e}")
        logger.error(f"Tipo de error: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Actualizar estado a error si tenemos el servicio
        if response_service and response_service.get('id'):
            try:
                await _update_service_status(response_service['id'], ESTADO_ERROR, response_service)
            except Exception as update_error:
                logger.error(f"Error al actualizar estado del servicio tras fallo: {update_error}")
        
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/services/remesas")
async def get_remesas(request: ServiceRemesaSchema):
    request_data = request.model_dump()

    if not request_data.get('pedimento'):
        raise HTTPException(status_code=400, detail="ID del pedimento es requerido")
    if not request_data.get('organizacion'):
        raise HTTPException(status_code=400, detail="ID de la organización es requerido")

    try:
        response_service = await rest_controller.get_pedimento_services(request_data.get('pedimento'), service_type=5)
    except Exception as e:
        logger.error(f"Error al obtener servicios de remesas: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener servicios de remesas")

    try:
        response_credentials = await rest_controller.get_vucem_credentials(
            response_service[0].get('pedimento', {}).get('contribuyente', '')
        )
    except Exception as e:
        logger.error(f"Error al obtener credenciales VUCEM: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener credenciales VUCEM")
    
    if not response_service or not response_credentials:
        raise HTTPException(status_code=500, detail="Error al obtener servicios de remesas o credenciales VUCEM")

    logger.info(f"Servicios de remesas obtenidos exitosamente: {response_service}")


    soap_response = await get_soap_remesas(
        credenciales=response_credentials[0],
        response_service=response_service[0],
        soap_controller=soap_controller
    )




    
    
    return soap_response

@router.post("/services/partidas")
async def get_partidas(request: ServiceRemesaSchema):
    request_data = request.model_dump()

    if not request_data.get('pedimento'):
        raise HTTPException(status_code=400, detail="ID del pedimento es requerido")
    if not request_data.get('organizacion'):
        raise HTTPException(status_code=400, detail="ID de la organización es requerido")

    try:
        response_service = await rest_controller.get_pedimento_services(request_data.get('pedimento'), service_type=4)
    except Exception as e:
        logger.error(f"Error al obtener servicios de partidas: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener servicios de partidas")

    
    try:
        response_credentials = await rest_controller.get_vucem_credentials(
            response_service[0].get('pedimento', {}).get('contribuyente', '')
        )
    except Exception as e:
        logger.error(f"Error al obtener credenciales VUCEM: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener credenciales VUCEM")

    partidas = []
    if response_service[0]['pedimento']['numero_partidas'] > 0:
        for partida in range(1, response_service[0]['pedimento']['numero_partidas'] + 1):
            procesado = await get_soap_partidas(
                credenciales=response_credentials[0],
                response_service=response_service[0],
                soap_controller=soap_controller,
                partida=str(partida)
            )
            partidas.append(partida)
    
    response_service[0]['partidas'] = partidas
    return response_service

@router.post("/pedimentos/estado_pedimento")
async def get_estado_pedimento(request: PedimentoRequest):
    pass

@router.post("/pedimentos/coves")
async def get_cove(request: PedimentoRequest):
    pass

@router.post("/pedimentos/edocument")
async def get_edocument(request: PedimentoRequest):
    pass
