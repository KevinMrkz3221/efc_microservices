import os
from string import Template
from typing import Dict, Any
from payload_structure.soap_models import *

class SOAPTemplateManager:
    """Gestor de plantillas SOAP"""
    
    def __init__(self):
        self.templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
        
    def _load_template(self, template_name: str) -> str:
        """Carga una plantilla XML desde archivo"""
        template_path = os.path.join(self.templates_dir, f"{template_name}.xml")
        with open(template_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def _render_template(self, template_content: str, **kwargs) -> str:
        """Renderiza una plantilla con los parámetros dados"""
        try:
            # Crear el objeto Template
            template = Template(template_content)
            
            # Hacer la sustitución
            try:
                rendered = template.substitute(**kwargs)
            except Exception:
                # Si template.substitute() falla, usar reemplazo manual
                rendered = template_content
                for key, value in kwargs.items():
                    placeholder = f"{{{key}}}"
                    rendered = rendered.replace(placeholder, str(value))
            
            # Verificar si se hizo la sustitución
            cambios_realizados = template_content != rendered
            
            if not cambios_realizados:
                # Fallback: reemplazo manual directo
                rendered = template_content
                for key, value in kwargs.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in template_content:
                        rendered = rendered.replace(placeholder, str(value))
            
            return rendered
            
        except Exception as e:
            print(f"Error al renderizar template: {e}")
            raise
    
    def generar_consulta_estado_pedimento(
        self, 
        credenciales: CredencialesSOAP,
        consulta: ConsultaEstadoPedimento
    ) -> str:
        """Genera XML para consultar estado de pedimento"""
        template = self._load_template('consultar_estado_pedimento')
        return self._render_template(
            template,
            username=credenciales.username,
            password=credenciales.password,
            numero_operacion=consulta.numero_operacion,
            aduana=consulta.aduana,
            patente=consulta.patente,
            pedimento=consulta.pedimento
        )
    
    def generar_consulta_pedimento_completo(
        self, 
        credenciales: CredencialesSOAP,
        consulta: ConsultaPedimentoCompleto
    ) -> str:
        """Genera XML para consultar pedimento completo"""
        template = self._load_template('consultar_pedimento_completo')

        render = self._render_template(
            template,
            username=credenciales.username,
            password=credenciales.password,
            aduana=consulta.aduana,
            patente=consulta.patente,
            pedimento=consulta.pedimento
        )
        return render
    
    def generar_consulta_partida(
        self, 
        credenciales: CredencialesSOAP,
        consulta: ConsultaPartida
    ) -> str:
        """Genera XML para consultar partida"""
        template = self._load_template('consultar_partida')
        return self._render_template(
            template,
            username=credenciales.username,
            password=credenciales.password,
            aduana=consulta.aduana,
            patente=consulta.patente,
            pedimento=consulta.pedimento,
            numero_operacion=consulta.numero_operacion,
            numero_partida=consulta.numero_partida
        )
    
    def generar_consulta_acuses(
        self, 
        credenciales: CredencialesSOAP,
        consulta: ConsultaAcuses
    ) -> str:
        """Genera XML para consultar acuses"""
        template = self._load_template('consultar_acuses')
        return self._render_template(
            template,
            username=credenciales.username,
            password=credenciales.password,
            id_edocument=consulta.id_edocument
        )
    
    def generar_consulta_remesas(
        self, 
        credenciales: CredencialesSOAP,
        consulta: ConsultaRemesas
    ) -> str:
        """Genera XML para consultar remesas"""
        template = self._load_template('consultar_remesas')
        return self._render_template(
            template,
            username=credenciales.username,
            password=credenciales.password,
            aduana=consulta.aduana,
            patente=consulta.patente,
            pedimento=consulta.pedimento
        )
    
    def test_template_rendering(self):
        """Método de prueba para verificar el renderizado de templates"""
        print("=== Testing Template Rendering ===")
        
        # Crear credenciales de prueba
        test_credentials = CredencialesSOAP(
            username="TEST_USER",
            password="TEST_PASSWORD"
        )
        
        # Crear consulta de prueba
        test_consulta = ConsultaPedimentoCompleto(
            aduana="070",
            patente="3842",
            pedimento="5007757"
        )
        
        try:
            # Probar el renderizado
            result = self.generar_consulta_pedimento_completo(
                credenciales=test_credentials,
                consulta=test_consulta
            )
            
            print("✅ Template renderizado exitosamente")
            print(f"Resultado contiene usuario: {'TEST_USER' in result}")
            print(f"Resultado contiene password: {'TEST_PASSWORD' in result}")
            print(f"Resultado contiene aduana: {'070' in result}")
            
        except Exception as e:
            print(f"❌ Error en test: {e}")
            return False
            
        return True
    
    def debug_template_file(self, template_name: str):
        """Debug: muestra el contenido de un archivo template"""
        try:
            template_path = os.path.join(self.templates_dir, f"{template_name}.xml")
            print(f"=== Debug Template: {template_name} ===")
            print(f"Ruta del archivo: {template_path}")
            print(f"Archivo existe: {os.path.exists(template_path)}")
            
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    print(f"Contenido del template:\n{content[:500]}...")
                    
                    # Buscar placeholders
                    import re
                    placeholders = re.findall(r'\{(\w+)\}', content)
                    print(f"Placeholders encontrados: {placeholders}")
            
        except Exception as e:
            print(f"Error al debuggear template: {e}")
