import logging
from fastapi import HTTPException
from controllers.RESTController import rest_controller
from typing import Dict, Any
import xml.etree.ElementTree as ET

from schemas.serviceSchema import ServiceBaseSchema


logger = logging.getLogger(__name__)

from controllers.XMLController import xml_controller


def validate_pedimento_data(response_service: Dict[str, Any], credenciales: Dict[str, Any]) -> tuple:
    """
    Valida y extrae los datos necesarios para la petición SOAP.
    
    Args:
        response_service: Respuesta del servicio con datos del pedimento
        credenciales: Credenciales VUCEM
        
    Returns:
        tuple: (username, password, aduana, patente, pedimento)
        
    Raises:
        HTTPException: Si faltan datos requeridos
    """
    # Validar credenciales
    username = credenciales.get('usuario')
    password = credenciales.get('password')
    
    if not username or not password:
        logger.error("Credenciales VUCEM incompletas")
        raise HTTPException(status_code=400, detail="Credenciales VUCEM incompletas")

    # Validar datos del pedimento
    pedimento_data = response_service.get('pedimento', {})
    aduana = pedimento_data.get('aduana')
    patente = pedimento_data.get('patente') 
    pedimento = pedimento_data.get('pedimento')
    
    if not all([aduana, patente, pedimento]):
        logger.error(f"Datos del pedimento incompletos - Aduana: {aduana}, Patente: {patente}, Pedimento: {pedimento}")
        raise HTTPException(status_code=400, detail="Datos del pedimento incompletos")
    
    return username, password, aduana, patente, pedimento

def soap_error(soap_response):
    """
    Verifica si la respuesta SOAP no contiene errores.
    
    Args:
        soap_response: Respuesta del servicio SOAP
        
    Returns:
        bool: True si no hay errores, False en caso contrario
    """
    if '<ns3:tieneError>true</ns3:tieneError>' in soap_response.text:
        return True
    
    # Aquí podrías agregar más lógica para verificar errores específicos en el XML
    return False

async def get_soap_pedimento_completo(credenciales, response_service, soap_controller):
    """
    Procesa la petición SOAP para obtener el pedimento completo y guarda el documento.
    
    Args:
        credenciales: Diccionario con credenciales VUCEM (usuario, password)
        response_service: Respuesta del servicio con datos del pedimento
        soap_controller: Instancia del controlador SOAP
        
    Returns:
        dict: Respuesta con el servicio, respuesta SOAP y documento guardado
        
    Raises:
        HTTPException: Si hay errores en la petición SOAP o al guardar el documento
    """
    try:
        # Extraer credenciales
        username, password, aduana, patente, pedimento = validate_pedimento_data(response_service, credenciales)

        logger.info(f"Datos para SOAP - Usuario: {username}, Aduana: {aduana}, Patente: {patente}, Pedimento: {pedimento}")
        
        # Generar template SOAP
        soap_xml = soap_controller.generate_pedimento_completo_template(
            username=username,
            password=password,
            aduana=aduana,
            patente=patente,
            pedimento=pedimento
        )

        # Realizar petición SOAP
        logger.info("Realizando petición SOAP...")
        
        # Headers específicos para este servicio SOAP
        soap_headers = {
            'Content-Type': 'text/xml; charset=utf-8'
        }
        
        soap_response = await soap_controller.make_request_async(
            "ventanilla-ws-pedimentos/ConsultarPedimentoCompletoService?wsdl", 
            data=soap_xml,
            headers=soap_headers
        )



        if (soap_response) and (not soap_error(soap_response)):
            logger.info(f"Petición SOAP exitosa - Status: {soap_response.status_code}")
            
            data = xml_controller.extract_data(soap_response.text)
            # Enviar el documento XML como respuesta
            document_response = await rest_controller.post_document(
                soap_response=soap_response,
                organizacion=response_service['organizacion'],
                pedimento=response_service['pedimento']['id']
            )

            data['organizacion'] = response_service['organizacion']
            data['id'] = response_service['pedimento']['id']

            return {
                "servicio": response_service,
                "documento": document_response,
                "xml_content": data
            }

        else:
            logger.error("Error en petición SOAP")
            raise HTTPException(status_code=500, detail="Error en la petición SOAP al servicio VUCEM")
            
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en get_pedimento_completo: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error interno al procesar pedimento completo: {str(e)}")

