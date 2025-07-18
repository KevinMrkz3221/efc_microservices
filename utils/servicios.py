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

async def _validate_request_data(request_data: Dict[str, Any]) -> None:
    """
    Valida los datos básicos requeridos en las peticiones.
    
    Args:
        request_data: Diccionario con datos de la petición
        
    Raises:
        HTTPException: Si faltan datos requeridos
    """
    if not request_data.get('pedimento'):
        logger.error("ID del pedimento no proporcionado en la petición")
        raise HTTPException(status_code=400, detail="ID del pedimento es requerido")
    
    if not request_data.get('organizacion'):
        logger.error("ID de la organización no proporcionado en la petición")
        raise HTTPException(status_code=400, detail="ID de la organización es requerido")
    
    logger.info(f"Validación exitosa - Pedimento: {request_data['pedimento']}, Organización: {request_data['organizacion']}")

async def _get_pedimento_service(pedimento_id: str, service_type: int, operation_name: str) -> Dict[str, Any]:
    """
    Obtiene el servicio de pedimento por tipo.
    
    Args:
        pedimento_id: ID del pedimento
        service_type: Tipo de servicio a obtener
        operation_name: Nombre de la operación para logging
        
    Returns:
        Dict con datos del servicio
        
    Raises:
        HTTPException: Si hay error al obtener el servicio
    """
    try:
        logger.info(f"Obteniendo servicio tipo {service_type} para pedimento {pedimento_id} - Operación: {operation_name}")
        response_service = await rest_controller.get_pedimento_services(pedimento_id, service_type=service_type)
        
        if not response_service or len(response_service) == 0:
            logger.error(f"No se encontró servicio tipo {service_type} para pedimento {pedimento_id}")
            raise HTTPException(status_code=404, detail=f"No se encontró servicio de {operation_name}")
        
        logger.info(f"Servicio obtenido exitosamente: {response_service[0].get('id', 'N/A')}")
        return response_service[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener servicio de {operation_name}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error al obtener servicio de {operation_name}")

async def _get_vucem_credentials(contribuyente_id: str, operation_name: str) -> Dict[str, Any]:
    """
    Obtiene las credenciales VUCEM para un contribuyente.
    
    Args:
        contribuyente_id: ID del contribuyente
        operation_name: Nombre de la operación para logging
        
    Returns:
        Dict con credenciales VUCEM
        
    Raises:
        HTTPException: Si hay error al obtener credenciales
    """
    try:
        logger.info(f"Obteniendo credenciales VUCEM para contribuyente {contribuyente_id} - Operación: {operation_name}")
        response_credentials = await rest_controller.get_vucem_credentials(contribuyente_id)
        
        if not response_credentials or len(response_credentials) == 0:
            logger.error(f"No se encontraron credenciales VUCEM para contribuyente {contribuyente_id}")
            raise HTTPException(status_code=404, detail="Credenciales VUCEM no encontradas")
        
        logger.info("Credenciales VUCEM obtenidas exitosamente")
        return response_credentials[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener credenciales VUCEM para {operation_name}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Error al obtener credenciales VUCEM")

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

async def _update_service_status(service_id: int, estado: int, response_service: dict, operation_name: str = "operación") -> bool:
    """
    Actualiza el estado del servicio de manera robusta.
    
    Args:
        service_id: ID del servicio
        estado: Nuevo estado (1=creado, 2=en proceso, 3=finalizado, 4=error)
        response_service: Datos del servicio
        operation_name: Nombre de la operación para logging
        
    Returns:
        bool: True si se actualizó exitosamente, False en caso contrario
    """
    estado_nombres = {
        1: "CREADO",
        2: "EN_PROCESO", 
        3: "FINALIZADO",
        4: "ERROR"
    }
    
    estado_nombre = estado_nombres.get(estado, f"DESCONOCIDO({estado})")
    
    try:
        logger.info(f"Actualizando estado del servicio {service_id} a {estado_nombre} - Operación: {operation_name}")
        
        update_data = {
            "estado": estado,
            "pedimento": response_service['pedimento']['id'],
            "organizacion": response_service['organizacion'],
        }
        
        result = await rest_controller.put_pedimento_service(service_id=service_id, data=update_data)
        
        if result is None:
            logger.error(f"Falló la actualización del estado del servicio {service_id} a {estado_nombre}")
            return False
        
        logger.info(f"Estado del servicio {service_id} actualizado exitosamente a {estado_nombre}")
        return True
        
    except Exception as e:
        logger.error(f"Error al actualizar estado del servicio {service_id} a {estado_nombre} - Operación {operation_name}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

async def _create_response(service_data: dict, additional_data: Optional[Dict[str, Any]] = None, 
                          success_message: str = "Operación completada exitosamente") -> Dict[str, Any]:
    """
    Crea una respuesta estandarizada para los endpoints.
    
    Args:
        service_data: Datos del servicio
        additional_data: Datos adicionales a incluir en la respuesta
        success_message: Mensaje de éxito personalizado
        
    Returns:
        Dict con estructura de respuesta estandarizada
    """
    response = {
        "success": True,
        "message": success_message,
        "data": {
            "organizacion": service_data['organizacion'],
            "servicio": service_data['id'],
            "estado": ESTADO_FINALIZADO,
            "pedimento_id": service_data['pedimento']['id']
        }
    }
    
    if additional_data:
        response["data"].update(additional_data)
    
    logger.info(f"Respuesta creada exitosamente para servicio {service_data['id']}")
    return response

async def _execute_service_safely(service_func, request_data: Dict[str, Any], service_name: str) -> Dict[str, Any]:
    """
    Ejecuta un servicio de manera segura capturando errores.
    
    Args:
        service_func: Función del servicio a ejecutar
        request_data: Datos para la petición
        service_name: Nombre del servicio para logging
        
    Returns:
        Dict con resultado de la ejecución
    """
    try:
        logger.info(f"Iniciando ejecución automática de {service_name}...")
        
        # Crear el objeto request apropiado
        from schemas.serviceSchema import ServiceRemesaSchema
        request_obj = ServiceRemesaSchema(**request_data)
        
        # Ejecutar el servicio
        result = await service_func(request_obj)
        
        logger.info(f"Servicio {service_name} ejecutado exitosamente")
        return {
            "success": True,
            "service_name": service_name,
            "result": result.body.decode() if hasattr(result, 'body') else str(result),
            "status_code": result.status_code if hasattr(result, 'status_code') else 200
        }
        
    except Exception as e:
        logger.error(f"Error en ejecución automática de {service_name}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "service_name": service_name,
            "error": str(e),
            "status_code": 500
        }

async def _execute_service_with_retry(service_func, request_data: Dict[str, Any], 
                                     service_name: str, max_retries: int = 2) -> Dict[str, Any]:
    """
    Ejecuta un servicio con reintentos automáticos en caso de fallo.
    
    Args:
        service_func: Función del servicio a ejecutar
        request_data: Datos para la petición
        service_name: Nombre del servicio para logging
        max_retries: Número máximo de reintentos
        
    Returns:
        Dict con resultado de la ejecución
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                wait_time = min(2 ** attempt, 30)  # Backoff exponencial, máximo 30 segundos
                logger.info(f"Reintentando {service_name} en {wait_time} segundos (intento {attempt + 1}/{max_retries + 1})")
                await asyncio.sleep(wait_time)
            
            result = await _execute_service_safely(service_func, request_data, service_name)
            
            if result["success"]:
                if attempt > 0:
                    logger.info(f"✅ Servicio {service_name} exitoso en intento {attempt + 1}")
                return result
            else:
                last_error = result.get("error", "Error desconocido")
                
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Intento {attempt + 1} fallido para {service_name}: {e}")
    
    # Si llegamos aquí, todos los intentos fallaron
    logger.error(f"❌ Servicio {service_name} falló después de {max_retries + 1} intentos. Último error: {last_error}")
    return {
        "success": False,
        "service_name": service_name,
        "error": f"Falló después de {max_retries + 1} intentos. Último error: {last_error}",
        "status_code": 500,
        "retries_attempted": max_retries + 1
    }

async def _wait_for_service_creation(pedimento_id: str, service_type: int, 
                                   timeout: int = 60, check_interval: int = 2) -> bool:
    """
    Espera a que un servicio sea creado antes de intentar ejecutarlo.
    
    Args:
        pedimento_id: ID del pedimento
        service_type: Tipo de servicio a esperar
        timeout: Tiempo máximo de espera en segundos
        check_interval: Intervalo entre verificaciones en segundos
        
    Returns:
        bool: True si el servicio fue encontrado, False si se agotó el timeout
    """
    start_time = asyncio.get_event_loop().time()
    
    logger.info(f"Esperando creación de servicio tipo {service_type} para pedimento {pedimento_id} (timeout: {timeout}s)")
    
    attempt = 0
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            attempt += 1
            services = await rest_controller.get_pedimento_services(pedimento_id, service_type=service_type)
            
            if services and len(services) > 0:
                logger.info(f"✅ Servicio tipo {service_type} encontrado para pedimento {pedimento_id} (intento {attempt})")
                return True
            else:
                if attempt % 10 == 0:  # Log cada 20 segundos aprox
                    logger.info(f"⏳ Servicio tipo {service_type} aún no encontrado para pedimento {pedimento_id} (intento {attempt}/{timeout//check_interval})")
                    
        except Exception as e:
            logger.warning(f"Error verificando servicio tipo {service_type}: {e}")
        
        await asyncio.sleep(check_interval)
    
    logger.error(f"❌ Timeout esperando servicio tipo {service_type} para pedimento {pedimento_id} después de {timeout}s")
    return False

async def _execute_follow_up_services(pedimento_id: str, organizacion_id: str, 
                                    has_remesas: bool = False, has_partidas: bool = False) -> Dict[str, Any]:
    """
    Ejecuta automáticamente los servicios de seguimiento después del pedimento completo.
    
    Args:
        pedimento_id: ID del pedimento
        organizacion_id: ID de la organización
        has_remesas: Si el pedimento tiene remesas
        has_partidas: Si el pedimento tiene partidas
        
    Returns:
        Dict con resultados de la ejecución
    """
    logger.info(f"Iniciando ejecución automática de servicios para pedimento {pedimento_id}")
    
    request_data = {
        "pedimento": pedimento_id,
        "organizacion": organizacion_id
    }
    
    # Lista de servicios a ejecutar con sus tipos correspondientes
    services_to_execute = []
    
    # Agregar partidas si el pedimento las tiene
    if has_partidas:
        services_to_execute.append(("partidas", get_partidas, 4))
    
    # Agregar remesas si el pedimento las tiene
    if has_remesas:
        services_to_execute.append(("remesas", get_remesas, 5))
    
    # Siempre agregar acuses (si existen documentos digitalizados)
    services_to_execute.append(("acuse", get_acuse, 6))
    
    # Resultados de ejecución
    execution_results = {
        "total_services": len(services_to_execute),
        "successful_services": 0,
        "failed_services": 0,
        "results": []
    }
    
    # Esperar un poco antes de iniciar para que se completen los servicios creados
    logger.info("Esperando a que se completen las creaciones de servicios...")
    await asyncio.sleep(10)  # Aumentado de 5 a 10 segundos
    
    # Ejecutar servicios secuencialmente para evitar sobrecarga
    for service_name, service_func, service_type in services_to_execute:
        try:
            logger.info(f"🔄 Iniciando procesamiento de {service_name}...")
            
            # Verificar que el servicio exista antes de ejecutar
            service_exists = await _wait_for_service_creation(pedimento_id, service_type, timeout=60)
            
            if not service_exists:
                execution_results["failed_services"] += 1
                execution_results["results"].append({
                    "success": False,
                    "service_name": service_name,
                    "error": f"Servicio tipo {service_type} no encontrado después de esperar",
                    "status_code": 404
                })
                logger.warning(f"⚠️ Servicio {service_name} no encontrado, saltando...")
                continue
            
            # Ejecutar servicio con reintentos
            result = await _execute_service_with_retry(service_func, request_data, service_name, max_retries=2)
            execution_results["results"].append(result)
            
            if result["success"]:
                execution_results["successful_services"] += 1
                logger.info(f"✅ Servicio {service_name} completado exitosamente")
            else:
                execution_results["failed_services"] += 1
                logger.warning(f"❌ Servicio {service_name} falló: {result.get('error', 'Error desconocido')}")
            
            # Esperar entre servicios para no sobrecargar
            await asyncio.sleep(3)
                
        except Exception as e:
            execution_results["failed_services"] += 1
            execution_results["results"].append({
                "success": False,
                "service_name": service_name,
                "error": f"Error crítico: {str(e)}",
                "status_code": 500
            })
            logger.error(f"💥 Error crítico en servicio {service_name}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Log de resumen
    success_rate = (execution_results["successful_services"] / execution_results["total_services"]) * 100 if execution_results["total_services"] > 0 else 0
    
    if execution_results["successful_services"] == execution_results["total_services"]:
        logger.info(f"🎉 Ejecución automática completada exitosamente - {execution_results['successful_services']}/{execution_results['total_services']} (100%)")
    else:
        logger.warning(f"⚠️ Ejecución automática completada con errores - Éxito: {execution_results['successful_services']}/{execution_results['total_services']} ({success_rate:.1f}%)")
    
    return execution_results

async def _schedule_follow_up_services(pedimento_id: str, organizacion_id: str, 
                                     xml_content: Dict[str, Any]) -> None:
    """
    Programa la ejecución de servicios de seguimiento en segundo plano.
    
    Args:
        pedimento_id: ID del pedimento
        organizacion_id: ID de la organización
        xml_content: Contenido XML del pedimento para determinar qué servicios ejecutar
    """
    try:
        # Determinar qué servicios ejecutar basado en el contenido del pedimento
        has_remesas = bool(xml_content.get('remesas', 0))
        has_partidas = xml_content.get('numero_partidas', 0) > 0
        
        logger.info(f"Programando servicios automáticos - Remesas: {has_remesas}, Partidas: {has_partidas}")
        
        # Crear tarea en segundo plano
        task = asyncio.create_task(
            _execute_follow_up_services(
                pedimento_id=pedimento_id,
                organizacion_id=organizacion_id,
                has_remesas=has_remesas,
                has_partidas=has_partidas
            )
        )
        
        # Agregar callback para logging cuando termine
        def log_completion(task):
            try:
                result = task.result()
                logger.info(f"Servicios automáticos completados para pedimento {pedimento_id}: {result['successful_services']}/{result['total_services']} exitosos")
            except Exception as e:
                logger.error(f"Error en servicios automáticos para pedimento {pedimento_id}: {e}")
        
        task.add_done_callback(log_completion)
        
        logger.info(f"Servicios automáticos programados exitosamente para pedimento {pedimento_id}")
        
    except Exception as e:
        logger.error(f"Error al programar servicios automáticos: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")


        logger.error(f"Error inesperado en {operation_name}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Actualizar estado a error si tenemos service_data
        if service_data:
            try:
                await _update_service_status(service_data['id'], ESTADO_ERROR, service_data, operation_name)
            except Exception as update_error:
                logger.error(f"Error al actualizar estado del servicio tras fallo: {update_error}")
        
        raise HTTPException(status_code=500, detail=f"Error interno en {operation_name}: {str(e)}")

def _log_operation_summary(operation_name: str, service_id: int, success: bool, 
                          additional_info: Optional[str] = None) -> None:
    """
    Registra un resumen de la operación realizada.
    
    Args:
        operation_name: Nombre de la operación
        service_id: ID del servicio procesado
        success: Si la operación fue exitosa
        additional_info: Información adicional opcional
    """
    status = "EXITOSO" if success else "FALLIDO"
    message = f"RESUMEN {operation_name.upper()}: {status} - Servicio ID: {service_id}"
    
    if additional_info:
        message += f" - {additional_info}"
    
    if success:
        logger.info(message)
    else:
        logger.error(message)

async def _validate_soap_controller() -> None:
    """
    Valida que el controlador SOAP esté disponible.
    
    Raises:
        HTTPException: Si el controlador SOAP no está disponible
    """
    if not soap_controller:
        logger.error("Controlador SOAP no disponible")
        raise HTTPException(status_code=500, detail="Servicio SOAP no disponible")