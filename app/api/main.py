from fastapi import APIRouter

from app.api.routes import (
    utils_router,
    whatsapp_router,
)

api_router = APIRouter()

api_router.include_router(utils_router, tags=["utils"])
# api_router.include_router(kavak_agent_router, tags=["kavak-agent"])
api_router.include_router(whatsapp_router, tags=["whatsapp"])
