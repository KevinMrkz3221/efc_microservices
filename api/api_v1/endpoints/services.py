from fastapi import APIRouter, HTTPException
from schemas.serviceSchema import ServiceBaseSchema

import asyncio
import logging
router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/services/")
async def get_service(request: ServiceBaseSchema):
    pass

