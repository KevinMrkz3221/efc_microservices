from fastapi import APIRouter, HTTPException
from schemas.pedimentoSchema import PedimentoRequest
from schemas.serviceSchema import ServiceBaseSchema, ServiceRemesaSchema
import asyncio
import logging
import traceback
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from controllers.RESTController import rest_controller
from controllers.SOAPController import soap_controller
from utils.peticiones import get_soap_pedimento_completo, get_soap_remesas, get_soap_partidas, get_soap_acuse, get_soap_edocument
from fastapi.responses import JSONResponse
from core.config import settings

from utils.servicios import *

# Estados del servicio
ESTADO_CREADO = 1
ESTADO_EN_PROCESO = 2  
ESTADO_FINALIZADO = 3
ESTADO_ERROR = 4

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/services/estado_pedimento")
async def get_estado_pedimento(request: ServiceRemesaSchema):
    """
    Obtiene el estado actual de un pedimento mediante consulta SOAP a VUCEM.
    
    Este endpoint:
    1. Obtiene el servicio de estado de pedimento existente
    2. Actualiza estado a "en proceso"
    3. Obtiene credenciales VUCEM
    4. Realiza petición SOAP para consultar estado
    5. Procesa y retorna información del estado
    
    Args:
        request: ServiceBaseSchema con pedimento y organización
        
    Returns:
        JSONResponse con estado actual del pedimento
        
    Raises:
        HTTPException: En caso de errores de validación o procesamiento
    """
    operation_name = "estado_pedimento"
    service_data = None
    
    try:
        # Validar datos de entrada
        request_data = request.model_dump()
        await _validate_request_data(request_data)
        
        logger.info(f"Iniciando consulta de estado de pedimento - Pedimento: {request_data['pedimento']}")
        
        # Obtener servicio de estado de pedimento existente
        service_data = await _get_pedimento_service(
            pedimento_id=request_data['pedimento'], 
            service_type=1, 
            operation_name=operation_name
        )
        
        # Actualizar estado a "En proceso"
        update_success = await _update_service_status(
            service_data['id'], ESTADO_EN_PROCESO, service_data, operation_name
        )

        if not update_success:
            raise HTTPException(status_code=500, detail="Error al actualizar estado del servicio")
        
        # Obtener credenciales VUCEM
        contribuyente_id = service_data.get('pedimento', {}).get('contribuyente', '')
        if not contribuyente_id:
            logger.error("No se encontró ID de contribuyente en los datos del servicio")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=400, detail="ID de contribuyente no encontrado")
            
        credentials = await _get_vucem_credentials(contribuyente_id, operation_name)
        
        # Procesar petición SOAP para obtener estado del pedimento
        logger.info("Realizando petición SOAP para estado del pedimento...")
        try:
            soap_response = await get_estado_pedimento(
                credenciales=credentials,
                response_service=service_data,
                soap_controller=soap_controller
            )
            
            if not soap_response:
                raise HTTPException(status_code=500, detail="Error en la petición SOAP para estado del pedimento")
            
            logger.info("Petición SOAP para estado del pedimento completada exitosamente")
            
        except HTTPException:
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise
        except Exception as e:
            logger.error(f"Error en petición SOAP para estado del pedimento: {e}")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=500, detail="Error en la petición SOAP al servicio VUCEM")
        
        # Finalizar servicio exitosamente
        await _update_service_status(service_data['id'], ESTADO_FINALIZADO, service_data, operation_name)
        
        # Crear respuesta estandarizada
        response_data = await _create_response(
            service_data=service_data,
            additional_data={
                "estado_pedimento": soap_response,
                "documento": soap_response.get('documento', {}),
                "xml_content": soap_response.get('xml_content', {})
            },
            success_message="Estado del pedimento consultado exitosamente"
        )
        
        logger.info(f"Consulta de estado de pedimento completada exitosamente - Servicio: {service_data['id']}")
        return JSONResponse(content=response_data, status_code=200)
        
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        pass
        logger.error(f"Error inesperado en {operation_name}: {e}")

@router.post("/services/listar_pedimentos")
async def get_listar_pedimentos(request: ServiceRemesaSchema):
    """
    Lista pedimentos disponibles en el sistema VUCEM para una organización.
    
    Este endpoint:
    1. Obtiene el servicio de listado de pedimentos existente
    2. Actualiza estado a "en proceso"
    3. Obtiene credenciales VUCEM
    4. Consulta lista de pedimentos en VUCEM
    5. Procesa y retorna la lista de pedimentos
    
    Args:
        request: ServiceBaseSchema con pedimento y organización
        
    Returns:
        JSONResponse con lista de pedimentos disponibles
        
    Raises:
        HTTPException: En caso de errores de validación o procesamiento
    """
    operation_name = "listar_pedimentos"
    service_data = None
    
    try:
        # Validar datos de entrada
        request_data = request.model_dump()
        await _validate_request_data(request_data)
        
        logger.info(f"Iniciando listado de pedimentos - Organización: {request_data['organizacion']}")
        
        # Obtener servicio de listado de pedimentos existente
        # Nota: Asumiendo que existe un tipo de servicio para listado (tipo 8)
        # Ajustar el tipo según la configuración del sistema
        try:
            services = await rest_controller.get_pedimento_services(
                request_data['pedimento'], 
                service_type=8  # Tipo para listado de pedimentos
            )
            
            if not services or len(services) == 0:
                logger.error(f"No se encontró servicio de listado de pedimentos")
                raise HTTPException(status_code=404, detail="Servicio de listado no encontrado")
                
            service_data = services[0]
            logger.info(f"Servicio de listado obtenido: {service_data.get('id', 'N/A')}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener servicio de listado: {e}")
            raise HTTPException(status_code=500, detail="Error al obtener servicio de listado")
        
        # Actualizar estado a "En proceso"
        update_success = await _update_service_status(
            service_data['id'], ESTADO_EN_PROCESO, service_data, operation_name
        )
        if not update_success:
            raise HTTPException(status_code=500, detail="Error al actualizar estado del servicio")
        
        # Obtener credenciales VUCEM
        contribuyente_id = service_data.get('pedimento', {}).get('contribuyente', '')
        if not contribuyente_id:
            logger.error("No se encontró ID de contribuyente en los datos del servicio")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=400, detail="ID de contribuyente no encontrado")
            
        credentials = await _get_vucem_credentials(contribuyente_id, operation_name)
        
        # Consultar pedimentos en VUCEM
        logger.info("Consultando pedimentos disponibles en VUCEM...")
        try:
            # Nota: Este endpoint requiere implementar la función específica en utils/peticiones.py
            # Por ahora, simularemos la respuesta básica
            
            # TODO: Implementar get_soap_lista_pedimentos en utils/peticiones.py
            # soap_response = await get_soap_lista_pedimentos(
            #     credenciales=credentials,
            #     response_service=service_data,
            #     soap_controller=soap_controller
            # )
            
            # Respuesta simulada para demostrar la estructura
            soap_response = {
                "pedimentos": [
                    {
                        "id": "PED001",
                        "numero": "24  44  1234  5678901",
                        "fecha": "2024-12-19",
                        "estado": "Tramitado",
                        "patente": "1234",
                        "aduana": "44"
                    }
                ],
                "total": 1,
                "documento": {
                    "filename": "lista_pedimentos.xml",
                    "size": 1024
                }
            }
            
            logger.info(f"Se encontraron {soap_response.get('total', 0)} pedimentos")
            
        except Exception as e:
            logger.error(f"Error en consulta SOAP de pedimentos: {e}")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=500, detail="Error en la consulta SOAP al servicio VUCEM")
        
        # Finalizar servicio exitosamente
        await _update_service_status(service_data['id'], ESTADO_FINALIZADO, service_data, operation_name)
        
        # Crear respuesta estandarizada
        response_data = await _create_response(
            service_data=service_data,
            additional_data={
                "pedimentos": soap_response.get('pedimentos', []),
                "total_pedimentos": soap_response.get('total', 0),
                "documento": soap_response.get('documento', {}),
                "fecha_consulta": "2024-12-19T12:00:00Z"
            },
            success_message=f"Se encontraron {soap_response.get('total', 0)} pedimentos disponibles"
        )
        
        # Agregar advertencia si no se encontraron pedimentos
        if soap_response.get('total', 0) == 0:
            response_data["warnings"] = [
                "No se encontraron pedimentos disponibles en el periodo consultado"
            ]
        
        logger.info(f"Listado de pedimentos completado - Total: {soap_response.get('total', 0)}")
        return JSONResponse(content=response_data, status_code=200)
        
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en {operation_name}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Actualizar estado a error si tenemos service_data
        if service_data:
            try:
                await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            except Exception as update_error:
                logger.error(f"Error al actualizar estado del servicio tras fallo: {update_error}")
        
        raise HTTPException(status_code=500, detail=f"Error interno en {operation_name}: {str(e)}")

@router.post("/services/pedimento_completo")
async def get_pedimento_completo(request: ServiceBaseSchema):
    """
    Obtiene el pedimento completo de VUCEM y procesa todos los documentos asociados.
    
    Este endpoint:
    1. Crea un servicio de pedimento completo
    2. Obtiene credenciales VUCEM
    3. Realiza petición SOAP para pedimento completo
    4. Actualiza datos del pedimento
    5. Procesa documentos digitalizados (e-documents)
    6. Crea servicios adicionales automáticamente
    
    Args:
        request: ServiceBaseSchema con pedimento y organización
        
    Returns:
        JSONResponse con datos del pedimento completo y servicios creados
        
    Raises:
        HTTPException: En caso de errores de validación o procesamiento
    """
    service_id = None
    operation_name = "pedimento_completo"
    
    try:
        # Validar datos de entrada
        request_data = request.model_dump()
        await _validate_request_data(request_data)
        
        logger.info(f"Iniciando procesamiento de pedimento completo - Pedimento: {request_data['pedimento']}")
        
        # Crear servicio de pedimento completo
        logger.info("Creando servicio de pedimento completo...")
        try:
            response_service = await rest_controller.post_pedimento_service(request_data)
            if not response_service:
                raise HTTPException(status_code=500, detail="No se pudo crear el servicio de pedimento")
            
            service_id = response_service['id']
            logger.info(f"Servicio creado exitosamente con ID: {service_id}")
            
        except Exception as e:
            logger.error(f"Error al crear servicio de pedimento completo: {e}")
            raise HTTPException(status_code=500, detail="Error al crear el servicio de pedimento")
        
        # Actualizar estado a "En proceso"
        update_success = await _update_service_status(
            service_id, ESTADO_EN_PROCESO, response_service, operation_name
        )
        if not update_success:
            raise HTTPException(status_code=500, detail="Error al actualizar estado del servicio")
        
        # Obtener credenciales VUCEM
        contribuyente_id = response_service['pedimento']['contribuyente']
        credentials = await _get_vucem_credentials(contribuyente_id, operation_name)
        
        # Procesar petición SOAP para obtener pedimento completo
        logger.info("Realizando petición SOAP para pedimento completo...")
        try:
            soap_response = await get_soap_pedimento_completo(
                credenciales=credentials,
                response_service=response_service,
                soap_controller=soap_controller
            )
            
            if not soap_response:
                raise HTTPException(status_code=500, detail="Error en la petición SOAP al servicio VUCEM")
            
            logger.info("Petición SOAP completada exitosamente")
            
        except HTTPException:
            await _update_service_status(service_id, ESTADO_ERROR, response_service, operation_name)
            raise
        except Exception as e:
            logger.error(f"Error en petición SOAP: {e}")
            await _update_service_status(service_id, ESTADO_ERROR, response_service, operation_name)
            raise HTTPException(status_code=500, detail="Error en la petición SOAP al servicio VUCEM")
        
        # Actualizar datos del pedimento con información del XML
        logger.info("Actualizando datos del pedimento...")
        try:
            xml_content = soap_response.get('xml_content', {})
            if xml_content:
                # Excluir 'identificadores_ed' del contenido a enviar
                update_content = {k: v for k, v in xml_content.items() if k != 'identificadores_ed'}
                
                pedimento_response = await rest_controller.put_pedimento(
                    response_service['pedimento']['id'],
                    update_content
                )
                logger.info("Pedimento actualizado exitosamente")
            else:
                logger.warning("No se recibió contenido XML para actualizar el pedimento")
                
        except Exception as e:
            logger.warning(f"No se pudo actualizar el pedimento (continuando proceso): {e}")
            # No fallar todo el proceso por este error
        
        # Procesar documentos digitalizados (e-documents)
        edocuments_result = []
        edocuments_error = None
        
        try:
            identificadores_ed = xml_content.get('identificadores_ed', [])
            if identificadores_ed:
                logger.info(f"Procesando {len(identificadores_ed)} documentos digitalizados...")
                edocuments_result = await _post_edocuments(
                    response_service=response_service,
                    identificadores_ed=identificadores_ed
                )
                logger.info(f"Se procesaron exitosamente {len(edocuments_result)} documentos digitalizados")
            else:
                logger.info("No se encontraron documentos digitalizados (identificadores ED)")
                
        except Exception as e:
            logger.error(f"Error al procesar documentos digitalizados: {e}")
            edocuments_error = str(e)
            # No fallar todo el proceso por este error
        
        # Crear servicios adicionales automáticamente
        servicios_adicionales = {}
        servicios_error = None
        
        try:
            logger.info("Creando servicios adicionales...")
            new_service_base = {
                "pedimento": response_service['pedimento']['id'],
                "organizacion": response_service['organizacion'],
                "estado": ESTADO_CREADO,
                "tipo_procesamiento": 2,
            }
            
            # Mapeo de servicios a crear
            servicios_config = [
                (4, "partidas"),     # Tipo 4 para partidas
                (6, "acuse"),        # Tipo 6 para acuse  
                (1, "estado_pedimento"),  # Tipo 1 para estado_pedimento
                (7, "edocument")     # Tipo 7 para edocument
            ]
            
            # Agregar servicio de remesas solo si el pedimento tiene remesas
            if xml_content.get('remesas', 0):
                servicios_config.append((5, "remesas"))
            
            for servicio_tipo, servicio_nombre in servicios_config:
                try:
                    logger.info(f"Creando servicio {servicio_nombre} (tipo {servicio_tipo})...")
                    new_service = {**new_service_base, "servicio": servicio_tipo}
                    service_response = await rest_controller.post_pedimento_service(new_service)
                    
                    if service_response:
                        servicios_adicionales[f"servicio_{servicio_nombre}"] = service_response['id']
                        logger.info(f"✅ Servicio {servicio_nombre} (tipo {servicio_tipo}) creado exitosamente con ID: {service_response['id']}")
                    else:
                        logger.error(f"❌ No se pudo crear el servicio {servicio_nombre} (tipo {servicio_tipo}) - respuesta vacía")
                        
                except Exception as e:
                    logger.error(f"❌ Error al crear servicio {servicio_nombre} (tipo {servicio_tipo}): {e}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    
        except Exception as e:
            logger.error(f"Error al crear servicios adicionales: {e}")
            servicios_error = str(e)
            # No fallar todo el proceso por este error
        
        # Log resumen de servicios creados
        logger.info(f"📋 Resumen servicios creados: {len(servicios_adicionales)} de {len(servicios_config)} servicios")
        for servicio_nombre, servicio_id in servicios_adicionales.items():
            logger.info(f"  ✅ {servicio_nombre}: ID {servicio_id}")
        
        # Finalizar servicio exitosamente
        await _update_service_status(service_id, ESTADO_FINALIZADO, response_service, operation_name)
        
        # Programar servicios automáticos en segundo plano
        logger.info("Programando ejecución automática de servicios de seguimiento...")
        try:
            await _schedule_follow_up_services(
                pedimento_id=response_service['pedimento']['id'],
                organizacion_id=response_service['organizacion'],
                xml_content=xml_content
            )
            logger.info("Servicios automáticos programados exitosamente")
        except Exception as e:
            logger.warning(f"No se pudieron programar servicios automáticos: {e}")
            # No fallar el proceso principal por esto
        
        # Construir respuesta final
        response_data = await _create_response(
            service_data=response_service,
            additional_data={
                "documento": soap_response.get('documento', {}),
                "xml_content": xml_content,
                "edocuments": edocuments_result,
                "servicios_adicionales": servicios_adicionales,
                "servicios_automaticos": {
                    "programados": True,
                    "remesas_programadas": bool(xml_content.get('remesas', 0)),
                    "partidas_programadas": xml_content.get('numero_partidas', 0) > 0,
                    "acuses_programados": True,
                    "mensaje": "Los servicios de partidas, remesas y acuses se ejecutarán automáticamente en segundo plano"
                }
            },
            success_message="Pedimento completo procesado exitosamente. Servicios automáticos programados."
        )
        
        # Agregar errores no críticos si los hay
        if edocuments_error:
            response_data["warnings"] = response_data.get("warnings", [])
            response_data["warnings"].append(f"Error en documentos digitalizados: {edocuments_error}")
            
        if servicios_error:
            response_data["warnings"] = response_data.get("warnings", [])
            response_data["warnings"].append(f"Error en servicios adicionales: {servicios_error}")
        
        logger.info(f"Pedimento completo procesado exitosamente - Servicio: {service_id}")
        return JSONResponse(content=response_data, status_code=200)
        
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en {operation_name}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Actualizar estado a error si tenemos el service_id
        if service_id:
            try:
                # Necesitamos response_service para actualizar estado
                if 'response_service' in locals():
                    await _update_service_status(service_id, ESTADO_ERROR, response_service, operation_name)
            except Exception as update_error:
                logger.error(f"Error al actualizar estado del servicio tras fallo: {update_error}")
        
        raise HTTPException(status_code=500, detail=f"Error interno en {operation_name}: {str(e)}")

@router.post("/services/partidas")
async def get_partidas(request: ServiceRemesaSchema):
    """
    Obtiene todas las partidas de un pedimento mediante peticiones SOAP a VUCEM.
    
    Este endpoint:
    1. Obtiene el servicio de partidas existente
    2. Actualiza estado a "en proceso"
    3. Obtiene credenciales VUCEM
    4. Procesa cada partida individualmente
    5. Guarda documentos XML de cada partida
    
    Args:
        request: ServiceRemesaSchema con pedimento y organización
        
    Returns:
        JSONResponse con lista de partidas procesadas
        
    Raises:
        HTTPException: En caso de errores de validación o procesamiento
    """
    operation_name = "partidas"
    service_data = None
    
    try:
        # Validar datos de entrada
        request_data = request.model_dump()
        await _validate_request_data(request_data)
        
        logger.info(f"Iniciando procesamiento de partidas - Pedimento: {request_data['pedimento']}")
        
        # Obtener servicio de partidas existente
        service_data = await _get_pedimento_service(
            pedimento_id=request_data['pedimento'], 
            service_type=4, 
            operation_name=operation_name
        )
        
        # Actualizar estado a "En proceso"
        update_success = await _update_service_status(
            service_data['id'], ESTADO_EN_PROCESO, service_data, operation_name
        )
        if not update_success:
            raise HTTPException(status_code=500, detail="Error al actualizar estado del servicio")
        
        # Obtener credenciales VUCEM
        contribuyente_id = service_data.get('pedimento', {}).get('contribuyente', '')
        if not contribuyente_id:
            logger.error("No se encontró ID de contribuyente en los datos del servicio")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=400, detail="ID de contribuyente no encontrado")
            
        credentials = await _get_vucem_credentials(contribuyente_id, operation_name)
        
        # Procesar partidas
        partidas_procesadas = []
        numero_partidas = service_data['pedimento'].get('numero_partidas', 0)
        
        logger.info(f"Procesando {numero_partidas} partidas...")
        
        if numero_partidas <= 0:
            logger.warning("El pedimento no tiene partidas para procesar")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=404, detail="No se encontraron partidas para el pedimento")
        
        # Procesar cada partida individualmente
        for partida_num in range(1, numero_partidas + 1):
            try:
                logger.info(f"Procesando partida {partida_num}/{numero_partidas}")
                
                # Aqui obtiene el xml
                soap_response = await get_soap_partidas(
                    credenciales=credentials,
                    response_service=service_data,
                    soap_controller=soap_controller,
                    partida=str(partida_num)
                )
                
                if soap_response:
                    partidas_procesadas.append({
                        "numero": partida_num,
                        "procesada": True,
                        "documento": soap_response.get('documento', {})
                    })
                    logger.info(f"Partida {partida_num} procesada exitosamente")
                else:
                    logger.warning(f"No se pudo procesar la partida {partida_num}")
                    partidas_procesadas.append({
                        "numero": partida_num,
                        "procesada": False,
                        "error": "Error en petición SOAP"
                    })
                    
            except Exception as e:
                logger.error(f"Error al procesar partida {partida_num}: {e}")
                partidas_procesadas.append({
                    "numero": partida_num,
                    "procesada": False,
                    "error": str(e)
                })
                # Continuar con las siguientes partidas
                continue
        
        # Verificar si se procesó al menos una partida
        partidas_exitosas = [p for p in partidas_procesadas if p.get('procesada', False)]
        
        if not partidas_exitosas:
            logger.error("No se pudo procesar ninguna partida")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=500, detail="No se pudo procesar ninguna partida")
        
        # Finalizar servicio exitosamente
        await _update_service_status(service_data['id'], ESTADO_FINALIZADO, service_data, operation_name)
        
        # Crear respuesta estandarizada
        response_data = await _create_response(
            service_data=service_data,
            additional_data={
                "partidas": partidas_procesadas,
                "total_partidas": numero_partidas,
                "partidas_exitosas": len(partidas_exitosas),
                "partidas_fallidas": len(partidas_procesadas) - len(partidas_exitosas)
            },
            success_message=f"Se procesaron {len(partidas_exitosas)}/{numero_partidas} partidas exitosamente"
        )
        
        # Agregar advertencias si hubo partidas fallidas
        if len(partidas_exitosas) < numero_partidas:
            response_data["warnings"] = [
                f"Se procesaron solo {len(partidas_exitosas)} de {numero_partidas} partidas"
            ]
        
        logger.info(f"Procesamiento de partidas completado - Exitosas: {len(partidas_exitosas)}/{numero_partidas}")
        return JSONResponse(content=response_data, status_code=200)
        
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en {operation_name}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Actualizar estado a error si tenemos service_data
        if service_data:
            try:
                await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            except Exception as update_error:
                logger.error(f"Error al actualizar estado del servicio tras fallo: {update_error}")
        
        raise HTTPException(status_code=500, detail=f"Error interno en {operation_name}: {str(e)}")

@router.post("/services/remesas")
async def get_remesas(request: ServiceRemesaSchema):
    """
    Obtiene las remesas de un pedimento mediante petición SOAP a VUCEM.
    
    Este endpoint:
    1. Obtiene el servicio de remesas existente  
    2. Actualiza estado a "en proceso"
    3. Obtiene credenciales VUCEM
    4. Realiza petición SOAP para remesas
    5. Guarda documento XML de remesas
    
    Args:
        request: ServiceRemesaSchema con pedimento y organización
        
    Returns:
        JSONResponse con datos de remesas procesadas
        
    Raises:
        HTTPException: En caso de errores de validación o procesamiento
    """
    operation_name = "remesas"
    service_data = None
    
    try:
        # Validar datos de entrada
        request_data = request.model_dump()
        await _validate_request_data(request_data)
        
        logger.info(f"Iniciando procesamiento de remesas - Pedimento: {request_data['pedimento']}")
        
        # Obtener servicio de remesas existente
        service_data = await _get_pedimento_service(
            pedimento_id=request_data['pedimento'], 
            service_type=5, 
            operation_name=operation_name
        )
        
        # Actualizar estado a "En proceso"
        update_success = await _update_service_status(
            service_data['id'], ESTADO_EN_PROCESO, service_data, operation_name
        )
        if not update_success:
            raise HTTPException(status_code=500, detail="Error al actualizar estado del servicio")
        
        # Obtener credenciales VUCEM
        contribuyente_id = service_data.get('pedimento', {}).get('contribuyente', '')
        if not contribuyente_id:
            logger.error("No se encontró ID de contribuyente en los datos del servicio")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=400, detail="ID de contribuyente no encontrado")
            
        credentials = await _get_vucem_credentials(contribuyente_id, operation_name)
        
        # Procesar petición SOAP para remesas
        logger.info("Realizando petición SOAP para remesas...")
        try:
            soap_response = await get_soap_remesas(
                credenciales=credentials,
                response_service=service_data,
                soap_controller=soap_controller
            )
            
            if not soap_response:
                raise HTTPException(status_code=500, detail="Error en la petición SOAP para remesas")
            
            logger.info("Petición SOAP para remesas completada exitosamente")
            
        except HTTPException:
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise
        except Exception as e:
            logger.error(f"Error en petición SOAP para remesas: {e}")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=500, detail="Error en la petición SOAP al servicio VUCEM")
        
        # Finalizar servicio exitosamente
        await _update_service_status(service_data['id'], ESTADO_FINALIZADO, service_data, operation_name)
        
        # Crear respuesta estandarizada
        response_data = await _create_response(
            service_data=service_data,
            additional_data={
                "remesas": soap_response,
                "documento": soap_response.get('documento', {})
            },
            success_message="Remesas procesadas exitosamente"
        )
        
        logger.info(f"Procesamiento de remesas completado exitosamente - Servicio: {service_data['id']}")
        return JSONResponse(content=response_data, status_code=200)
        
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en {operation_name}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Actualizar estado a error si tenemos service_data
        if service_data:
            try:
                await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            except Exception as update_error:
                logger.error(f"Error al actualizar estado del servicio tras fallo: {update_error}")
        
        raise HTTPException(status_code=500, detail=f"Error interno en {operation_name}: {str(e)}")

@router.post("/services/acuse")
async def get_acuse(request: ServiceRemesaSchema):
    """
    Obtiene los acuses de documentos digitalizados de un pedimento mediante peticiones SOAP a VUCEM.
    
    Este endpoint:
    1. Obtiene el servicio de acuse existente
    2. Actualiza estado a "en proceso"
    3. Obtiene credenciales VUCEM
    4. Obtiene lista de documentos digitalizados (e-documents)
    5. Procesa cada documento para obtener su acuse en PDF
    6. Guarda cada PDF procesado
    
    Args:
        request: ServiceRemesaSchema con pedimento y organización
        
    Returns:
        JSONResponse con lista de documentos digitalizados procesados
        
    Raises:
        HTTPException: En caso de errores de validación o procesamiento
    """
    operation_name = "acuse"
    service_data = None
    
    try:
        # Validar datos de entrada
        request_data = request.model_dump()
        await _validate_request_data(request_data)
        
        logger.info(f"Iniciando procesamiento de acuses - Pedimento: {request_data['pedimento']}")
        
        # Obtener servicio de acuse existente
        service_data = await _get_pedimento_service(
            pedimento_id=request_data['pedimento'], 
            service_type=6, 
            operation_name=operation_name
        )
        
        # Actualizar estado a "En proceso"
        update_success = await _update_service_status(
            service_data['id'], ESTADO_EN_PROCESO, service_data, operation_name
        )
        if not update_success:
            raise HTTPException(status_code=500, detail="Error al actualizar estado del servicio")
        
        # Obtener credenciales VUCEM
        contribuyente_id = service_data.get('pedimento', {}).get('contribuyente', '')
        if not contribuyente_id:
            logger.error("No se encontró ID de contribuyente en los datos del servicio")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=400, detail="ID de contribuyente no encontrado")
            
        credentials = await _get_vucem_credentials(contribuyente_id, operation_name)
        
        # Obtener documentos digitalizados (e-documents)
        logger.info("Obteniendo documentos digitalizados...")
        try:
            edocs = await rest_controller.get_edocs(service_data['pedimento']['id'])
            
            if not edocs:
                logger.warning("No se encontraron documentos digitalizados para el pedimento")
                await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
                raise HTTPException(status_code=404, detail="No se encontraron documentos digitalizados para el pedimento")
            
            logger.info(f"Se encontraron {len(edocs)} documentos digitalizados")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener documentos digitalizados: {e}")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=500, detail="Error al obtener documentos digitalizados")
        
        # Procesar acuses de documentos digitalizados
        documentos_procesados = []
        documentos_exitosos = 0
        
        logger.info(f"Procesando acuses para {len(edocs)} documentos...")
        
        for idx, edoc in enumerate(edocs):
            documento_info = {
                "clave": edoc.get('clave', 'N/A'),
                "descripcion": edoc.get('descripcion', 'N/A'),
                "numero_edocument": edoc.get('numero_edocument', 'N/A'),
                "procesado": False,
                "error": None
            }
            
            # Verificar que el documento tenga número de e-document
            if not edoc.get('numero_edocument'):
                logger.warning(f"Documento {idx + 1} no tiene numero_edocument, saltando...")
                documento_info["error"] = "Sin número de e-document"
                documentos_procesados.append(documento_info)
                continue
            
            try:
                logger.info(f"Procesando acuse para documento {idx + 1}: {edoc['numero_edocument']}")
                
                soap_response = await get_soap_acuse(
                    credenciales=credentials,
                    response_service=service_data,
                    soap_controller=soap_controller,
                    edocument=edoc,
                    idx=idx + 1
                )
                
                if soap_response:
                    documento_info["procesado"] = True
                    documento_info["documento"] = soap_response.get('documento', {})
                    documentos_exitosos += 1
                    logger.info(f"Acuse del documento {idx + 1} procesado exitosamente")
                else:
                    documento_info["error"] = "Error en petición SOAP"
                    logger.warning(f"No se pudo procesar el acuse del documento {idx + 1}")
                
            except Exception as e:
                logger.error(f"Error al procesar acuse del documento {idx + 1}: {e}")
                documento_info["error"] = str(e)
                # Continuar con los siguientes documentos
            
            documentos_procesados.append(documento_info)
        
        # Verificar si se procesó al menos un documento
        if documentos_exitosos == 0:
            logger.error("No se pudo procesar ningún acuse de documento digitalizado")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=500, detail="No se pudo procesar ningún acuse de documento digitalizado")
        
        # Finalizar servicio exitosamente
        await _update_service_status(service_data['id'], ESTADO_FINALIZADO, service_data, operation_name)
        
        # Crear respuesta estandarizada
        response_data = await _create_response(
            service_data=service_data,
            additional_data={
                "edocumentos": documentos_procesados,
                "total_documentos": len(edocs),
                "documentos_exitosos": documentos_exitosos,
                "documentos_fallidos": len(edocs) - documentos_exitosos
            },
            success_message=f"Se procesaron {documentos_exitosos}/{len(edocs)} acuses de documentos exitosamente"
        )
        
        # Agregar advertencias si hubo documentos fallidos
        if documentos_exitosos < len(edocs):
            response_data["warnings"] = [
                f"Se procesaron solo {documentos_exitosos} de {len(edocs)} documentos digitalizados"
            ]
        
        logger.info(f"Procesamiento de acuses completado - Exitosos: {documentos_exitosos}/{len(edocs)}")
        return JSONResponse(content=response_data, status_code=200)
        
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en {operation_name}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Actualizar estado a error si tenemos service_data
        if service_data:
            try:
                await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            except Exception as update_error:
                logger.error(f"Error al actualizar estado del servicio tras fallo: {update_error}")
        
        raise HTTPException(status_code=500, detail=f"Error interno en {operation_name}: {str(e)}")

@router.post("/services/edocument")
async def get_edocument(request: ServiceRemesaSchema):
    """
    Obtiene y procesa todos los documentos digitalizados (e-documents) de un pedimento.
    
    Este endpoint:
    1. Obtiene el servicio de documentos digitalizados existente
    2. Actualiza estado a "en proceso"
    3. Obtiene credenciales VUCEM
    4. Obtiene lista de documentos digitalizados
    5. Procesa cada documento para obtener su edocument
    6. Retorna lista de documentos procesados
    
    Args:
        request: PedimentoRequest con pedimento y organización
        
    Returns:
        JSONResponse con lista de documentos digitalizados procesados
        
    Raises:
        HTTPException: En caso de errores de validación o procesamiento
    """
    operation_name = "edocument"
    service_data = None
    
    try:
        # Validar datos de entrada
        request_data = request.model_dump()
        await _validate_request_data(request_data)
        
        logger.info(f"Iniciando procesamiento de e-documents - Pedimento: {request_data['pedimento']}")
        
        # Obtener servicio de documentos digitalizados existente
        service_data = await _get_pedimento_service(
            pedimento_id=request_data['pedimento'], 
            service_type=7, 
            operation_name=operation_name
        )
        
        # Actualizar estado a "En proceso"
        update_success = await _update_service_status(
            service_data['id'], ESTADO_EN_PROCESO, service_data, operation_name
        )
        if not update_success:
            raise HTTPException(status_code=500, detail="Error al actualizar estado del servicio")
        
        # Obtener credenciales VUCEM
        contribuyente_id = service_data.get('pedimento', {}).get('contribuyente', '')
        if not contribuyente_id:
            logger.error("No se encontró ID de contribuyente en los datos del servicio")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=400, detail="ID de contribuyente no encontrado")
            
        credentials = await _get_vucem_credentials(contribuyente_id, operation_name)
        
        # Obtener documentos digitalizados
        logger.info("Obteniendo documentos digitalizados...")
        try:
            edocs = await rest_controller.get_edocs(service_data['pedimento']['id'])
            
            if not edocs:
                logger.warning("No se encontraron documentos digitalizados para el pedimento")
                await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
                raise HTTPException(status_code=404, detail="No se encontraron documentos digitalizados para el pedimento")
            
            logger.info(f"Se encontraron {len(edocs)} documentos digitalizados")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener documentos digitalizados: {e}")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=500, detail="Error al obtener documentos digitalizados")
        
        # Procesar documentos digitalizados
        documentos_procesados = []
        documentos_exitosos = 0
        
        logger.info(f"Procesando {len(edocs)} documentos digitalizados...")
        
        for idx, edoc in enumerate(edocs):
            documento_info = {
                "clave": edoc.get('clave', 'N/A'),
                "descripcion": edoc.get('descripcion', 'N/A'),
                "numero_edocument": edoc.get('numero_edocument', 'N/A'),
                "procesado": False,
                "error": None
            }
            
            # Verificar que el documento tenga número de e-document
            if not edoc.get('numero_edocument'):
                logger.warning(f"Documento {idx + 1} no tiene numero_edocument, saltando...")
                documento_info["error"] = "Sin número de e-document"
                documentos_procesados.append(documento_info)
                continue
            
            try:
                logger.info(f"Procesando e-document {idx + 1}: {edoc['numero_edocument']}")
                
                # Procesar acuse del documento
                soap_response = await get_soap_edocument(
                    credenciales=credentials,
                    response_service=service_data,
                    soap_controller=soap_controller,
                    edocument=edoc,
                    idx=idx + 1
                )
                
                if soap_response:
                    documento_info["procesado"] = True
                    documento_info["documento"] = soap_response.get('documento', {})
                    documentos_exitosos += 1
                    logger.info(f"E-document {idx + 1} procesado exitosamente")
                else:
                    documento_info["error"] = "Error en petición SOAP"
                    logger.warning(f"No se pudo procesar el e-document {idx + 1}")
                
            except Exception as e:
                logger.error(f"Error al procesar e-document {idx + 1}: {e}")
                documento_info["error"] = str(e)
                # Continuar con los siguientes documentos
            
            documentos_procesados.append(documento_info)
        
        # Verificar si se procesó al menos un documento
        if documentos_exitosos == 0:
            logger.error("No se pudo procesar ningún documento digitalizado")
            await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            raise HTTPException(status_code=500, detail="No se pudo procesar ningún documento digitalizado")
        
        # Finalizar servicio exitosamente
        await _update_service_status(service_data['id'], ESTADO_FINALIZADO, service_data, operation_name)
        
        # Crear respuesta estandarizada
        response_data = await _create_response(
            service_data=service_data,
            additional_data={
                "edocumentos": documentos_procesados,
                "total_documentos": len(edocs),
                "documentos_exitosos": documentos_exitosos,
                "documentos_fallidos": len(edocs) - documentos_exitosos
            },
            success_message=f"Se procesaron {documentos_exitosos}/{len(edocs)} documentos digitalizados exitosamente"
        )
        
        # Agregar advertencias si hubo documentos fallidos
        if documentos_exitosos < len(edocs):
            response_data["warnings"] = [
                f"Se procesaron solo {documentos_exitosos} de {len(edocs)} documentos digitalizados"
            ]
        
        logger.info(f"Procesamiento de e-documents completado - Exitosos: {documentos_exitosos}/{len(edocs)}")
        return JSONResponse(content=response_data, status_code=200)
        
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en {operation_name}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Actualizar estado a error si tenemos service_data
        if service_data:
            try:
                await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            except Exception as update_error:
                logger.error(f"Error al actualizar estado del servicio tras fallo: {update_error}")
        
        raise HTTPException(status_code=500, detail=f"Error interno en {operation_name}: {str(e)}")

@router.post("/services/coves") # Sin Testear
async def get_cove(request: ServiceRemesaSchema):
    pass





