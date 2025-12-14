"""
Main FastAPI Application

Simplified application setup for Kavak agent - no database dependencies.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config.logging.config import RequestContextMiddleware
from app.core.manager import settings, lifespan
from app.api.main import api_router


def initialize_application() -> FastAPI:
    """Initialize and configure the FastAPI application."""
    app = FastAPI(**settings.set_app_attributes, lifespan=lifespan)
    
    # Add request context middleware
    app.add_middleware(RequestContextMiddleware)

    # Configure CORS
    _configure_cors(app)

    # Include routers
    app.include_router(router=api_router, prefix=settings.API_PREFIX)

    return app


def _configure_cors(app: FastAPI) -> None:
    """Configure CORS middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
        allow_credentials=True,
        expose_headers=["*"],
    )


# Create the application instance
app = initialize_application()
