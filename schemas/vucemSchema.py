from fastapi import FastAPI
from pydantic import BaseModel
from uuid import UUID 

class VucemSchema(BaseModel):
    id: str
    organization_id: str
    user: str
    password: str
    patente: str
    is_importer: bool
    acuseCove: bool
    acuseedocument: bool
    is_active: bool

