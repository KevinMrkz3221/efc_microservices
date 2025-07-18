import xml.etree.ElementTree as ET
from dataclasses import dataclass

# Pedimento Completo
@dataclass
class XMLScraper: # Clase me extrae datos de Pedimento
    """
    Clase para manejar la extracción de datos de un XML.
    """

    def _get_numero_operacion(self, root: ET.Element) -> str:
        """
        Método para obtener el número de operación del XML.
        
        Args:
            root: Elemento raíz del XML.
        
        Returns:
            Número de operación como string.
        """
        numero_operacion = root.find('.//ns2:numeroOperacion', namespaces={'ns2': 'http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/consultarpedimentocompleto'})
        return numero_operacion.text if numero_operacion is not None else None
    
    def _get_pedimento(self, root: ET.Element) -> str:
        """
        Método para obtener el pedimento del XML.
        
        Args:
            root: Elemento raíz del XML.
        
        Returns:
            Pedimento como string.
        """
        pedimento = root.find('.//ns2:pedimento/ns2:pedimento', namespaces={'ns2': 'http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/consultarpedimentocompleto'})
        return pedimento.text if pedimento is not None else None

    def _get_curp_apoderado(self, root: ET.Element) -> str:
        """
        Método para obtener el CURP del apoderado del XML.
        
        Args:
            root: Elemento raíz del XML.
        
        Returns:
            CURP del apoderado como string.
        """
        curp_apoderado = root.find('.//ns2:curpApoderadomandatario', namespaces={'ns2': 'http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/consultarpedimentocompleto'})
        return curp_apoderado.text if curp_apoderado is not None else None
    
    def _get_agente_aduanal(self, root: ET.Element) -> str:
        """
        Método para obtener el RFC del agente aduanal del XML.
        
        Args:
            root: Elemento raíz del XML.
        
        Returns:
            RFC del agente aduanal como string.
        """
        agente_aduanal = root.find('.//ns2:rfcAgenteAduanalSocFactura', namespaces={'ns2': 'http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/consultarpedimentocompleto'})
        return agente_aduanal.text if agente_aduanal is not None else None
    
    def _get_partidas(self, root: ET.Element) -> int:
        """
        Método para obtener el número máximo de partidas del XML.
        
        Args:
            root: Elemento raíz del XML.
        
        Returns:
            Número máximo de partidas como entero.
        """
        partidas_elements = root.findall('.//ns2:partidas', namespaces={'ns2': 'http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/consultarpedimentocompleto'})
        partidas_values = []
        for elem in partidas_elements:
            try:
                if elem.text is not None:
                    partidas_values.append(int(elem.text))
            except ValueError:
                continue
        
        return max(partidas_values) if partidas_values else None

    def _get_identificadores_ed(self, root: ET.Element) -> list:
        """
        Método para obtener todos los identificadores con clave 'ED' del XML.
        
        Args:
            root: Elemento raíz del XML.
        
        Returns:
            Lista de diccionarios con los datos de identificadores ED.
        """
        namespaces = {
            'ns2': 'http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/consultarpedimentocompleto',
            'ns': 'http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/comunes'
        }
        identificadores_ed = []
        
        # Buscar todos los elementos identificadores
        identificadores_elements = root.findall('.//ns2:identificadores/ns2:identificadores', namespaces)
                
        for identificador in identificadores_elements:
            try:
                # Extraer la clave del identificador (está dentro de claveIdentificador con namespace)
                clave_elem = identificador.find('ns:claveIdentificador/ns:clave', namespaces)
                clave = clave_elem.text if clave_elem is not None else None
                
                # Solo procesar si la clave es 'ED'
                if clave == 'ED':
                    # Extraer descripción (con namespace)
                    descripcion_elem = identificador.find('ns:claveIdentificador/ns:descripcion', namespaces)
                    descripcion = descripcion_elem.text if descripcion_elem is not None else None
                    
                    # Extraer complemento1 (con namespace)
                    complemento1_elem = identificador.find('ns:complemento1', namespaces)
                    complemento1 = complemento1_elem.text if complemento1_elem is not None else None
                                        
                    # Agregar a la lista si tenemos los datos básicos
                    if clave and complemento1:
                        identificadores_ed.append({
                            'clave': clave,
                            'descripcion': descripcion,
                            'complemento1': complemento1
                        })
                        
            except Exception as e:
                # Log del error pero continuar procesando otros identificadores
                print(f"Error procesando identificador: {e}")
                continue
        
        return identificadores_ed

    def _remesas(self, root: ET.Element) -> bool:
        """
        Método para verificar si el pedimento tiene remesas.
        Busca identificadores con clave 'RC' (REMESAS DE CONSOLIDADO).
        
        Args:
            root: Elemento raíz del XML.
        
        Returns:
            True si encuentra identificadores con clave 'RC', False en caso contrario.
        """
        namespaces = {
            'ns2': 'http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/consultarpedimentocompleto',
            'ns': 'http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/comunes'
        }
        
        # Buscar todos los elementos identificadores
        identificadores_elements = root.findall('.//ns2:identificadores/ns2:identificadores', namespaces)
        
        for identificador in identificadores_elements:
            try:
                # Extraer la clave del identificador
                clave_elem = identificador.find('ns:claveIdentificador/ns:clave', namespaces)
                clave = clave_elem.text if clave_elem is not None else None
                
                # Si encontramos una clave 'RC', el pedimento tiene remesas
                if clave == 'RC':
                    return True
                        
            except Exception as e:
                # Log del error pero continuar procesando otros identificadores
                print(f"Error procesando identificador para remesas: {e}")
                continue
        
        print("No se encontraron remesas (sin identificadores RC)")
        return False

    def _get_tipo_operacion(self, root: ET.Element) -> str:
        """
        Método para obtener el tipo de operación del XML.
        
        Args:
            root: Elemento raíz del XML.
        
        Returns:
            Tipo de operación como string.
        """
        tipo_operacion = root.find('.//ns2:tipoOperacion/ns2:clave', namespaces={'ns2': 'http://www.ventanillaunica.gob.mx/pedimentos/ws/oxml/consultarpedimentocompleto'})
        return tipo_operacion.text if tipo_operacion is not None else None
    
    def extract_data(self, xml_content: str) -> dict:
        """
        Método para extraer datos específicos del XML.
        
        Args:
            xml_content: Contenido del XML como string.
        
        Returns:
            Diccionario con los datos extraídos.
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Extraer datos con manejo de errores individual
            data = {}
            
            data['numero_operacion'] = self._get_numero_operacion(root)
            data['pedimento'] = self._get_pedimento(root)
            data['curp_apoderado'] = self._get_curp_apoderado(root)
            data['agente_aduanal'] = self._get_agente_aduanal(root)
            data['numero_partidas'] = self._get_partidas(root)
            data['identificadores_ed'] = self._get_identificadores_ed(root)
            data['remesas'] = self._remesas(root)
            data['tipo_operacion'] = self._get_tipo_operacion(root)

            # Verificar que se extrajeron los datos esenciales
            if not any([data['numero_operacion'], data['pedimento'], data['curp_apoderado'], data['agente_aduanal']]):
                return {}
            
            return data
            
        except ET.ParseError as e:
            print(f"Error al parsear el XML: {e}")
            return {}
        except Exception as e:
            print(f"Error inesperado al extraer datos del XML: {e}")
            return {}

        return extract_xml_data(xml_content)


class XMLControllerRemesas:
    pass

class XMLControllerPartidas:
    pass

xml_controller = XMLScraper()