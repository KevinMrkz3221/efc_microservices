from pydantic import BaseModel, Field, field_validator
from typing import Optional
from uuid import UUID


class PedimentoBaseSchema(BaseModel):
    """Esquema base para pedimentos con campos comunes"""
    aduana: str = Field(..., min_length=3, max_length=3, description="Código de aduana (3 dígitos)", pattern="^[0-9]{3}$")
    patente: str = Field(..., min_length=4, max_length=4, description="Número de patente (4 dígitos)", pattern="^[0-9]{4}$")
    pedimento: str = Field(..., min_length=7, max_length=7, description="Número de pedimento (7 dígitos)", pattern="^[0-9]{7}$")
    
    @field_validator('aduana')
    def validate_aduana(cls, v):
        if not v.isdigit():
            raise ValueError('Aduana debe contener solo dígitos')
        return v
    
    @field_validator('patente')
    def validate_patente(cls, v):
        if not v.isdigit():
            raise ValueError('Patente debe contener solo dígitos')
        return v
    
    @field_validator('pedimento')
    def validate_pedimento(cls, v):
        if not v.isdigit():
            raise ValueError('Pedimento debe contener solo dígitos')
        return v


class PedimentoRequest(PedimentoBaseSchema):
    """Esquema para solicitudes de pedimento"""
    pedimento_id: str = Field(..., description="ID único del pedimento")
    organizacion_id: str = Field(..., description="ID de la organización")
    
    @field_validator('pedimento_id', 'organizacion_id')
    def validate_ids(cls, v):
        if not v or not v.strip():
            raise ValueError('Los IDs no pueden estar vacíos')
        return v.strip()


class PedimentoCompletoRequest(PedimentoBaseSchema):
    """Esquema para solicitar pedimento completo"""
    username: str = Field(..., min_length=3, max_length=50, description="Usuario para autenticación")
    password: str = Field(..., min_length=1, description="Contraseña para autenticación")
    
    @field_validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username no puede estar vacío')
        return v.strip()


class EstadoPedimentoRequest(PedimentoBaseSchema):
    """Esquema para consultar estado de pedimento"""
    username: str = Field(..., min_length=3, max_length=50, description="Usuario para autenticación")
    password: str = Field(..., min_length=1, description="Contraseña para autenticación")
    numero_operacion: str = Field(..., min_length=1, max_length=20, description="Número de operación del pedimento")
    
    @field_validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username no puede estar vacío')
        return v.strip()
    
    @field_validator('numero_operacion')
    def validate_numero_operacion(cls, v):
        if not v or not v.strip():
            raise ValueError('Número de operación no puede estar vacío')
        return v.strip()


class RemesasRequest(PedimentoBaseSchema):
    """Esquema para consultar remesas"""
    username: str = Field(..., min_length=3, max_length=50, description="Usuario para autenticación")
    password: str = Field(..., min_length=1, description="Contraseña para autenticación")
    numero_operacion: str = Field(..., min_length=1, max_length=20, description="Número de operación del pedimento")
    
    @field_validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username no puede estar vacío')
        return v.strip()
    
    @field_validator('numero_operacion')
    def validate_numero_operacion(cls, v):
        if not v or not v.strip():
            raise ValueError('Número de operación no puede estar vacío')
        return v.strip()


class PedimentoResponse(BaseModel):
    """Esquema para respuestas de pedimento"""
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo de la operación")
    pedimento_id: Optional[str] = Field(None, description="ID del pedimento procesado")
    organizacion_id: Optional[str] = Field(None, description="ID de la organización")
    task_id: Optional[str] = Field(None, description="ID de la tarea en segundo plano")
    data: Optional[dict] = Field(None, description="Datos adicionales de la respuesta")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Pedimento procesado exitosamente",
                "pedimento_id": "12345",
                "organizacion_id": "org-123",
                "task_id": "task-abc-123",
                "data": {}
            }
        }