from fastapi import FastAPI
from pydantic import BaseModel
from uuid import UUID 

class AcuseSchema(BaseModel):
    document_id: str


