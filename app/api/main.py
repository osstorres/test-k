from fastapi import APIRouter
from app.api.routes import utils_router

api_router = APIRouter()

api_router.include_router(utils_router, tags=["utils"])
