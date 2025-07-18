import xml.etree.ElementTree as ET
import base64
import re

def extract_and_save_pdf_from_xml(xml_path, output_pdf_path):
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()

    root = ET.fromstring(xml_content)
    # Buscar el tag <File> con o sin namespace
    file_tag = root.find('.//File')
    if file_tag is None:
        # Buscar con namespace si existe
        for elem in root.iter():
            if elem.tag.endswith('File'):
                file_tag = elem
                break

    if file_tag is not None and file_tag.text and file_tag.text.strip():
        # Limpiar contenido base64 (remover espacios, saltos de línea, etc.)
        cleaned_content = re.sub(r'[\s\n\r\t]', '', file_tag.text)
        try:
            pdf_bytes = base64.b64decode(cleaned_content)
            with open(output_pdf_path, 'wb') as pdf_file:
                pdf_file.write(pdf_bytes)
            print(f"PDF guardado exitosamente en: {output_pdf_path}")
        except Exception as e:
            print(f"Error al decodificar el contenido base64: {e}")
    else:
        print("No se encontró el tag <File> o está vacío.")

# Ejemplo de uso
extract_and_save_pdf_from_xml('test.xml', 'output.pdf')