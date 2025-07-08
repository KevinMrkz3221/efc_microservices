from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ServiceBaseSchema(BaseModel):
    """Esquema base para servicios con campos comunes"""
    estado: int = Field(..., description="ID único del servicio")
    tipo_procesamiento: int = Field(..., description="ID de la organización")
    pedimento: str = Field(..., description="ID del estado del servicio")
    servicio: int = Field(..., description="ID del tipo de servicio")
    organizacion: str = Field(..., description="ID de la organización")
    
   
    
    @field_validator('pedimento', 'organizacion')
    def validate_string_fields(cls, v):
        if not v or not v.strip():
            raise ValueError('Los campos de texto no pueden estar vacíos')
        return v.strip()
    
    @field_validator('estado', 'tipo_procesamiento', 'servicio')
    def validate_numeric_ids(cls, v):
        if v is None or v < 0:
            raise ValueError('Los IDs numéricos deben ser números positivos')
        return v
    
