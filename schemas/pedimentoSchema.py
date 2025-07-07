from fastapi import FastAPI
from pydantic import BaseModel
from uuid import UUID 

class PedimentoRequest(BaseModel):
    pedimento_id: str
    organizacion_id: str

