import requests
import asyncio
import logging
from schemas.pedimentoSchema import PedimentoRequest
from dataclasses import dataclass
import concurrent.futures
import threading
from controllers.SOAPController import soap_controller  # 🔥 Usar instancia global

logger = logging.getLogger(__name__)


# Función asíncrona para el proceso en segundo plano
async def proceso_pedimento_completo_background(pedimento_id: str, organizacion_id: str):
    """
    Proceso que se ejecuta en segundo plano sin esperar respuesta
    """
    try:
        logger.info(f"Iniciando proceso en segundo plano para pedimento {pedimento_id}")
        
        # Simular un proceso que tarda tiempo
        await asyncio.sleep(2)  # Simula una operación que tarda 2 segundos
        
        # Aquí irían las llamadas SOAP usando la instancia global
        logger.info(f"Procesando pedimento {pedimento_id} con organización {organizacion_id}")
        
        # Ejemplo de llamada SOAP usando la instancia global
        soap_data = f"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <GetPedimentoCompleto>
                    <pedimento_id>{pedimento_id}</pedimento_id>
                    <organizacion_id>{organizacion_id}</organizacion_id>
                </GetPedimentoCompleto>
            </soap:Body>
        </soap:Envelope>
        """
        
        # 🔥 Usar la instancia global en lugar de crear una nueva
        response = soap_controller.make_request(
            endpoint="GetPedimentoCompleto",
            data=soap_data,
            headers={'SOAPAction': 'GetPedimentoCompleto'}
        )
        
        # Simular más procesamiento
        await asyncio.sleep(3)  # Simula más trabajo
        
        logger.info(f"Proceso completado para pedimento {pedimento_id}")
        
        # Aquí podrías guardar el resultado en una base de datos,
        # enviar una notificación, etc.
        
    except Exception as e:
        logger.error(f"Error en proceso background para pedimento {pedimento_id}: {e}")

# Función para disparar el proceso en segundo plano
async def disparar_proceso_pedimento_completo(pedimento_id: str, organizacion_id: str):
    """
    Dispara el proceso en segundo plano y retorna respuesta inmediata
    """
    # Crear la tarea en segundo plano SIN await
    task = asyncio.create_task(
        proceso_pedimento_completo_background(pedimento_id, organizacion_id)
    )
    
    # Opcional: Agregar callback para manejar errores
    task.add_done_callback(lambda t: logger.info(f"Tarea completada para pedimento {pedimento_id}"))
    
    # Retornar respuesta inmediata
    return {
        "pedimento_id": pedimento_id,
        "organizacion_id": organizacion_id,
        "status": "processing",
        "message": "El proceso ha sido iniciado en segundo plano",
        "task_id": str(id(task))  # ID único de la tarea
    }


