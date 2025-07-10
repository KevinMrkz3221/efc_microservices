import logging
from fastapi import HTTPException
from controllers.RESTController import rest_controller
from typing import Dict, Any
import xml.etree.ElementTree as ET
import base64
import re

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
    numero_operacion = pedimento_data.get('numero_operacion')
    
    if not all([aduana, patente, pedimento]):
        logger.error(f"Datos del pedimento incompletos - Aduana: {aduana}, Patente: {patente}, Pedimento: {pedimento}")
        raise HTTPException(status_code=400, detail="Datos del pedimento incompletos")
    
    return username, password, aduana, patente, pedimento, numero_operacion

def extract_acuse_documento_from_soap(soap_response_text):
    """
    Extrae el contenido del tag <acuseDocumento> de la respuesta SOAP multipart.
    
    Args:
        soap_response_text (str): Contenido de la respuesta SOAP
        
    Returns:
        str: Contenido Base64 del acuseDocumento o None si no se encuentra
    """
    try:
        # Primero, extraer la parte XML del contenido multipart
        xml_start = soap_response_text.find('<?xml')
        if xml_start == -1:
            logger.error("No se encontró contenido XML en la respuesta SOAP")
            return None
        
        # Extraer solo la parte XML
        xml_content = soap_response_text[xml_start:]
        
        # Si hay más contenido multipart después, cortarlo
        boundary_end = xml_content.find('--uuid:')
        if boundary_end != -1:
            xml_content = xml_content[:boundary_end]
        
        # Parsear el XML
        root = ET.fromstring(xml_content.strip())
        
        # Buscar el elemento acuseDocumento con namespaces
        namespaces = {
            'S': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns3': 'http://www.ventanillaunica.gob.mx/ws/consulta/acuses/'
        }
        
        # Buscar el elemento acuseDocumento
        acuse_elemento = root.find('.//ns3:responseConsultaAcuses/acuseDocumento', namespaces)
        
        if acuse_elemento is None:
            # Intentar sin namespace
            acuse_elemento = root.find('.//acuseDocumento')
        
        if acuse_elemento is not None and acuse_elemento.text:
            return acuse_elemento.text.strip()
        else:
            logger.error("No se encontró el tag <acuseDocumento> o está vacío")
            return None
    
    except ET.ParseError as e:
        logger.error(f"Error parseando XML: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extrayendo acuseDocumento: {e}")
        return None

def decode_acuse_base64_content(base64_content):
    """
    Decodifica el contenido Base64 del acuse y limpia caracteres especiales.
    
    Args:
        base64_content (str): Contenido codificado en Base64
        
    Returns:
        bytes: Contenido decodificado o None si hay error
    """
    try:
        # Limpiar el contenido Base64 de manera exhaustiva
        cleaned_content = base64_content
        
        # Remover entidades HTML/XML como &#xd;, &#xa;, etc.
        cleaned_content = re.sub(r'&#x[0-9a-fA-F]+;', '', cleaned_content)
        cleaned_content = re.sub(r'&#[0-9]+;', '', cleaned_content)
        
        # Remover espacios en blanco, saltos de línea, etc.
        cleaned_content = re.sub(r'[\s\n\r\t]', '', cleaned_content)
        
        # Remover caracteres no válidos para Base64
        cleaned_content = re.sub(r'[^A-Za-z0-9+/=]', '', cleaned_content)
        
        logger.info(f"Contenido Base64 limpiado: {len(cleaned_content)} caracteres")
        
        # Agregar padding si es necesario
        missing_padding = len(cleaned_content) % 4
        if missing_padding:
            cleaned_content += '=' * (4 - missing_padding)
            logger.info(f"Padding agregado: {4 - missing_padding} caracteres '='")
        
        # Decodificar Base64
        decoded_content = base64.b64decode(cleaned_content)
        
        logger.info(f"Contenido decodificado exitosamente: {len(decoded_content)} bytes")
        return decoded_content
    
    except Exception as e:
        logger.error(f"Error decodificando Base64: {e}")
        
        # Intentar con validación estricta deshabilitada
        try:
            logger.info("Intentando decodificación con validación relajada...")
            decoded_content = base64.b64decode(cleaned_content, validate=False)
            logger.info("¡Decodificación exitosa con validación relajada!")
            return decoded_content
        except Exception as e2:
            logger.error(f"Error también con validación relajada: {e2}")
            return None

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
        username, password, aduana, patente, pedimento, _ = validate_pedimento_data(response_service, credenciales)

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
            remesas = 1 if data.get('remesas', 0) else 2
            patente = response_service['pedimento'].get('patente', 'N/A')
            aduana = response_service['pedimento'].get('aduana', 'N/A')
            no_partidas = data.get('numero_partidas', 0)
            tipo_operacion = data.get('tipo_operacion', 'N/A')
            pedimento = response_service['pedimento'].get('pedimento', 'N/A')
            
            _file_name = f"vu_PC_{remesas}{no_partidas}{tipo_operacion}_{aduana}_{patente}_{pedimento}.xml"
            # Enviar el documento XML como respuesta
            document_response = await rest_controller.post_document(
                soap_response=soap_response,
                organizacion=response_service['organizacion'],
                pedimento=response_service['pedimento']['id'],
                file_name=_file_name,
                document_type=2
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

async def get_soap_remesas(credenciales, response_service, soap_controller):
    """
    Procesa la petición SOAP para obtener remesas y guarda el documento.
    
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
        username, password, aduana, patente, pedimento, numero_operacion = validate_pedimento_data(response_service, credenciales)

        logger.info(f"Datos para SOAP - Usuario: {username}, Aduana: {aduana}, Patente: {patente}, Pedimento: {pedimento}, Numero Operacion: {numero_operacion}")
        
        # Generar template SOAP
        soap_xml = soap_controller.generate_remesas_template(
            username=username,
            password=password,
            aduana=aduana,
            patente=patente,
            pedimento=pedimento,
            numero_operacion=numero_operacion
        )

        # Realizar petición SOAP
        logger.info("Realizando petición SOAP...")
        
        # Headers específicos para este servicio SOAP
        soap_headers = {
            'Content-Type': 'text/xml; charset=utf-8'
        }
        
        soap_response = await soap_controller.make_request_async(
            "ventanilla-ws-pedimentos/ConsultarRemesasService?wsdl", 
            data=soap_xml,
            headers=soap_headers
        )



        if (soap_response) and (not soap_error(soap_response)):
            logger.info(f"Petición SOAP exitosa - Status: {soap_response.status_code}")
            
            # data = xml_controller.extract_data(soap_response.text)
            # # Enviar el documento XML como respuesta
            remesas = 1 if response_service['pedimento'].get('remesas', 0) else 0
            patente = response_service['pedimento'].get('patente', 'N/A')
            aduana = response_service['pedimento'].get('aduana', 'N/A')
            no_partidas = response_service['pedimento'].get('numero_partidas', 0)
            tipo_operacion = response_service['pedimento'].get('tipo_operacion', 'N/A')
            pedimento = response_service['pedimento'].get('pedimento', 'N/A')
            
            _file_name = f"vu_RM_{remesas}{no_partidas}{tipo_operacion}_{aduana}_{patente}_{pedimento}.xml"

            document_response = await rest_controller.post_document(
                soap_response=soap_response,
                organizacion=response_service['organizacion'],
                pedimento=response_service['pedimento']['id'],
                file_name=_file_name,
                document_type=3
            )


            return {
                "servicio": response_service,
                "documento": document_response
            }

        else:
            logger.error("Error en petición SOAP")
            raise HTTPException(status_code=500, detail="Error en la petición SOAP al servicio VUCEM")
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en get_remesas: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error interno al procesar remesas: {str(e)}")

async def get_soap_partidas(credenciales, response_service, soap_controller, partida):
    """
    Procesa la petición SOAP para obtener partidas de un pedimento y guarda el documento.
    
    Args:
        credenciales: Diccionario con credenciales VUCEM (usuario, password)
        response_service: Respuesta del servicio con datos del pedimento
        soap_controller: Instancia del controlador SOAP
        partida: Número de partida a consultar
        
    Returns:
        dict: Respuesta con el servicio, respuesta SOAP y documento guardado
        
    Raises:
        HTTPException: Si hay errores en la petición SOAP o al guardar el documento
    """
    try:
        # Extraer credenciales
        username, password, aduana, patente, pedimento, numero_operacion = validate_pedimento_data(response_service, credenciales)

        logger.info(f"Datos para SOAP - Usuario: {username}, Aduana: {aduana}, Patente: {patente}, Pedimento: {pedimento}, Numero Operacion: {numero_operacion}, Partida: {partida}")
        
        # Generar template SOAP
        soap_xml = soap_controller.generate_partidas_template(
            username=username,
            password=password,
            aduana=aduana,
            patente=patente,
            pedimento=pedimento,
            numero_operacion=numero_operacion,
            partida=partida
        )

        # Realizar petición SOAP
        logger.info("Realizando petición SOAP...")
        
        # Headers específicos para este servicio SOAP
        soap_headers = {
            'Content-Type': 'text/xml; charset=utf-8'
        }
        
        soap_response = await soap_controller.make_request_async(
            "ventanilla-ws-pedimentos/ConsultarPartidaService?wsdl", 
            data=soap_xml,
            headers=soap_headers
        )


        if (soap_response) and (not soap_error(soap_response)):
            logger.info(f"Petición SOAP exitosa - Status: {soap_response.status_code}")

            remesas = 1 if response_service['pedimento'].get('remesas', 0) else 0
            patente = response_service['pedimento'].get('patente', 'N/A')
            aduana = response_service['pedimento'].get('aduana', 'N/A')
            no_partidas = response_service['pedimento'].get('numero_partidas', 0)
            tipo_operacion = response_service['pedimento'].get('tipo_operacion', 'N/A')
            pedimento = response_service['pedimento'].get('pedimento', 'N/A')
            
            _file_name = f"vu_PT_{remesas}{no_partidas}{tipo_operacion}_{aduana}_{patente}_{pedimento}_{partida}.xml"
            
            # Enviar el documento XML como respuesta
            document_response = await rest_controller.post_document(
                soap_response=soap_response,
                organizacion=response_service['organizacion'],
                pedimento=response_service['pedimento']['id'],
                file_name=_file_name,
                document_type=1
            )



            return {
                "servicio": response_service, 
                "documento": document_response

            }
        else:
            logger.error("Error en petición SOAP")
            raise HTTPException(status_code=500, detail="Error en la petición SOAP al servicio VUCEM")
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en get_partidas: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error interno al procesar partidas: {str(e)}")

async def get_soap_acuse(credenciales, response_service, soap_controller, edocument, idx):
    """
    Procesa la petición SOAP para obtener el acuse de un pedimento y guarda el documento.
    
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
        username, password, aduana, patente, pedimento, numero_operacion = validate_pedimento_data(response_service, credenciales)

        logger.info(f"Datos para SOAP - Usuario: {username}, Aduana: {aduana}, Patente: {patente}, Pedimento: {pedimento}, Numero Operacion: {numero_operacion}")
        
        # Generar template SOAP
        soap_xml = soap_controller.generate_acuse_template(
            username=username,
            password=password,
            idEDocument=edocument['numero_edocument']
        )

        # Realizar petición SOAP
        logger.info("Realizando petición SOAP...")
        
        # Headers específicos para este servicio SOAP
        soap_headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://www.ventanillaunica.gob.mx/ventanilla/ConsultaAcusesService/consultarAcuseEdocument',
            'Accept-Encoding': 'gzip,deflate',
        }
        
        soap_response = await soap_controller.make_request_async(
            "ventanilla-acuses-HA/ConsultaAcusesServiceWS?wsdl", 
            data=soap_xml,
            headers=soap_headers
        )
        

        if (soap_response) and (not soap_error(soap_response)):
            logger.info(f"Petición SOAP exitosa - Status: {soap_response.status_code}")

            # Extraer contenido Base64 del acuse
            logger.info("Extrayendo documento binario del acuse...")
            acuse_base64 = extract_acuse_documento_from_soap(soap_response.text)

            
            if not acuse_base64:
                logger.error("No se pudo extraer el contenido del acuseDocumento")
                raise HTTPException(status_code=500, detail="No se pudo extraer el documento del acuse")
            
            # Decodificar contenido Base64
            logger.info("Decodificando contenido Base64...")
            pdf_bytes = decode_acuse_base64_content(acuse_base64)
            
            if not pdf_bytes:
                logger.error("No se pudo decodificar el contenido Base64 del acuse")
                raise HTTPException(status_code=500, detail="No se pudo decodificar el documento del acuse")
            
            # Verificar que es un PDF válido
            if not pdf_bytes.startswith(b'%PDF'):
                logger.warning("El contenido decodificado no parece ser un PDF válido")
                # Continuar de todos modos, podría ser otro tipo de documento
            
            # Generar nombre del archivo
            remesas = 1 if response_service['pedimento'].get('remesas', 0) else 0
            patente = response_service['pedimento'].get('patente', 'N/A')
            aduana = response_service['pedimento'].get('aduana', 'N/A')
            no_partidas = response_service['pedimento'].get('numero_partidas', 0)
            tipo_operacion = response_service['pedimento'].get('tipo_operacion', 'N/A')
            pedimento = response_service['pedimento'].get('pedimento', 'N/A')
            _file_name = f"vu_AC_{remesas}{no_partidas}{tipo_operacion}_{aduana}_{patente}_{pedimento}_{idx}.pdf"
            
            # Enviar el documento PDF usando binary_content
            logger.info(f"Enviando documento PDF: {_file_name} ({len(pdf_bytes)} bytes)")
            document_response = await rest_controller.post_document(
                binary_content=pdf_bytes,
                organizacion=response_service['organizacion'],
                pedimento=response_service['pedimento']['id'],
                file_name=_file_name,
                document_type=4
            )
            return {
                "servicio": response_service,
                "documento": document_response
            }
        else:
            logger.error("Error en petición SOAP")
            raise HTTPException(status_code=500, detail="Error en la petición SOAP al servicio VUCEM")
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en get_acuse: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error interno al procesar acuse: {str(e)}")

async def get_estado_pedimento(credenciales, response_service, soap_controller):
    try:
        # Extraer credenciales
        username, password, aduana, patente, pedimento, numero_operacion = validate_pedimento_data(response_service, credenciales)

        logger.info(f"Datos para SOAP - Usuario: {username}, Aduana: {aduana}, Patente: {patente}, Pedimento: {pedimento}")
        
        # Generar template SOAP
        soap_xml = soap_controller.generate_estado_pedimento_template(
            username=username,
            password=password,
            aduana=aduana,
            patente=patente,
            pedimento=pedimento,
            numero_operacion=numero_operacion
        )

        # Realizar petición SOAP
        logger.info("Realizando petición SOAP...")
        
        # Headers específicos para este servicio SOAP
        soap_headers = {
            'Content-Type': 'text/xml; charset=utf-8'
        }
        
        soap_response = await soap_controller.make_request_async(
            "webservice-pedimentos-HA/consultarEstadoPedimento", 
            data=soap_xml,
            headers=soap_headers
        )



        if (soap_response) and (not soap_error(soap_response)):
            logger.info(f"Petición SOAP exitosa - Status: {soap_response.status_code}")
            
            data = xml_controller.extract_data(soap_response.text)
            remesas = 1 if data.get('remesas', 0) else 2
            patente = response_service['pedimento'].get('patente', 'N/A')
            aduana = response_service['pedimento'].get('aduana', 'N/A')
            no_partidas = data.get('numero_partidas', 0)
            tipo_operacion = data.get('tipo_operacion', 'N/A')
            pedimento = response_service['pedimento'].get('pedimento', 'N/A')
            
            _file_name = f"vu_EP_{remesas}{no_partidas}{tipo_operacion}_{aduana}_{patente}_{pedimento}.xml"
            # Enviar el documento XML como respuesta
            document_response = await rest_controller.post_document(
                soap_response=soap_response,
                organizacion=response_service['organizacion'],
                pedimento=response_service['pedimento']['id'],
                file_name=_file_name,
                document_type=6
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

async def get_soap_edocument(credenciales, response_service, soap_controller, edocument, idx):
    """
    Procesa la petición SOAP para obtener el acuse de un pedimento y guarda el documento.
    
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
        username, password, aduana, patente, pedimento, numero_operacion = validate_pedimento_data(response_service, credenciales)

        logger.info(f"Datos para SOAP - Usuario: {username}, Aduana: {aduana}, Patente: {patente}, Pedimento: {pedimento}, Numero Operacion: {numero_operacion}")
        
        # Generar template SOAP
        soap_xml = soap_controller.generate_edocument_template(
            username=username,
            password=password,
            idEDocument=edocument['numero_edocument']
        )

        # Realizar petición SOAP
        logger.info("Realizando petición SOAP...")
        
        # Headers específicos para este servicio SOAP
        soap_headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'http://tempuri.org/IServicioEdocument/GetDocumento',
            'Accept-Encoding': 'gzip,deflate',
        }
        
        soap_response = await soap_controller.make_request_async(
            "ventanilla-acuses-HA/ConsultaAcusesServiceWS?wsdl", 
            data=soap_xml,
            headers=soap_headers
        )
        

        if (soap_response) and (not soap_error(soap_response)):
            logger.info(f"Petición SOAP exitosa - Status: {soap_response.status_code}")

            # Extraer contenido Base64 del acuse
            logger.info("Extrayendo documento binario del acuse...")
            acuse_base64 = extract_acuse_documento_from_soap(soap_response.text)

            
            if not acuse_base64:
                logger.error("No se pudo extraer el contenido del acuseDocumento")
                raise HTTPException(status_code=500, detail="No se pudo extraer el documento del acuse")
            
            # Decodificar contenido Base64
            logger.info("Decodificando contenido Base64...")
            pdf_bytes = decode_acuse_base64_content(acuse_base64)
            
            if not pdf_bytes:
                logger.error("No se pudo decodificar el contenido Base64 del acuse")
                raise HTTPException(status_code=500, detail="No se pudo decodificar el documento del acuse")
            
            # Verificar que es un PDF válido
            if not pdf_bytes.startswith(b'%PDF'):
                logger.warning("El contenido decodificado no parece ser un PDF válido")
                # Continuar de todos modos, podría ser otro tipo de documento
            
            # Generar nombre del archivo
            remesas = 1 if response_service['pedimento'].get('remesas', 0) else 0
            patente = response_service['pedimento'].get('patente', 'N/A')
            aduana = response_service['pedimento'].get('aduana', 'N/A')
            no_partidas = response_service['pedimento'].get('numero_partidas', 0)
            tipo_operacion = response_service['pedimento'].get('tipo_operacion', 'N/A')
            pedimento = response_service['pedimento'].get('pedimento', 'N/A')
            _file_name = f"vu_EDC_{remesas}{no_partidas}{tipo_operacion}_{aduana}_{patente}_{pedimento}_{idx}.pdf"
            
            # Enviar el documento PDF usando binary_content
            logger.info(f"Enviando documento PDF: {_file_name} ({len(pdf_bytes)} bytes)")
            document_response = await rest_controller.post_document(
                binary_content=pdf_bytes,
                organizacion=response_service['organizacion'],
                pedimento=response_service['pedimento']['id'],
                file_name=_file_name,
                document_type=4
            )
            return {
                "servicio": response_service,
                "documento": document_response
            }
        else:
            logger.error("Error en petición SOAP")
            raise HTTPException(status_code=500, detail="Error en la petición SOAP al servicio VUCEM")
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        raise
    except Exception as e:
        logger.error(f"Error inesperado en get_acuse: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error interno al procesar acuse: {str(e)}")
