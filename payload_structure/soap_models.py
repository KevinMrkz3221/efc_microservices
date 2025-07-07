from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class CredencialesSOAP:
    """Credenciales para autenticación SOAP"""
    username: str
    password: str

@dataclass
class CredencialesVUCEM:
    """Credenciales VUCEM obtenidas desde la API"""
    id: str
    usuario: str
    password: str
    patente: str
    is_importador: bool
    acusecove: bool
    acuseedocument: bool
    is_active: bool
    created_at: str
    updated_at: str
    created_by: str
    updated_by: str
    organizacion: str
    
    def to_soap_credentials(self) -> CredencialesSOAP:
        """Convierte a credenciales SOAP"""
        return CredencialesSOAP(
            username=self.usuario,
            password=self.password
        )

@dataclass
class PedimentoBase:
    """Datos base de un pedimento"""
    aduana: str
    patente: str
    pedimento: str

@dataclass
class ConsultaEstadoPedimento(PedimentoBase):
    """Parámetros para consultar estado de pedimento"""
    numero_operacion: str

@dataclass
class ConsultaPedimentoCompleto(PedimentoBase):
    """Parámetros para consultar pedimento completo"""
    pass

@dataclass
class ConsultaPartida(PedimentoBase):
    """Parámetros para consultar partida"""
    numero_operacion: str
    numero_partida: str

@dataclass
class ConsultaAcuses:
    """Parámetros para consultar acuses"""
    id_edocument: str

@dataclass
class ConsultaRemesas(PedimentoBase):
    """Parámetros para consultar remesas"""
    # Agregar campos específicos según necesidades
    numero_operacion: str
    
