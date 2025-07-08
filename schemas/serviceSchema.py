from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID


class ServiceBaseSchema(BaseModel):
    """Esquema base para servicios con campos comunes"""
    service_id: UUID = Field(..., description="ID único del servicio")
    organization_id: UUID = Field(..., description="ID de la organización")
    status_id: int = Field(..., description="ID del estado del servicio")
    service_id: int = Field(..., description="ID del servicio")
    service_type_id: int = Field(..., description="ID del tipo de servicio")

    @field_validator('service_name')
    def validate_service_name(cls, v):
        if not v or not v.strip():
            raise ValueError('El nombre del servicio no puede estar vacío')
        return v.strip()
    
