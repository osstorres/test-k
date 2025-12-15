from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config.logging.config import RequestContextMiddleware
from app.core.manager import settings, lifespan
from app.api.main import api_router


def initialize_application() -> FastAPI:
    app = FastAPI(**settings.set_app_attributes, lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware)
    _configure_cors(app)
    app.include_router(router=api_router, prefix=settings.API_PREFIX)
    return app


def _configure_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
        allow_credentials=True,
        expose_headers=["*"],
    )


app = initialize_application()
