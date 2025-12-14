from pydantic_settings import BaseSettings
from typing import Dict, Any
import decouple
from app.core import Environment
from ..database.vector_config import VectorDBSettings
from .kavak_config import KavakSettings
import pathlib

ROOT_DIR: pathlib.Path = pathlib.Path(__file__).parent.parent.parent.resolve()


class ApplicationSettings(
    BaseSettings,
    VectorDBSettings,
):
    kavak: KavakSettings = KavakSettings()

    TITLE: str = "Kavak Agent API"
    VERSION: str = "1.0.0"
    TIMEZONE: str = "UTC"
    DESCRIPTION: str | None = None
    DEBUG: bool = False
    ENVIRONMENT: Environment = Environment.PRODUCTION

    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = decouple.config("PORT", default=8000, cast=int)
    SERVER_WORKERS: int = decouple.config("BACKEND_SERVER_WORKERS", default=1, cast=int)

    TIMEOUT_KEEP_ALIVE: int = 65
    LIMIT_MAX_REQUESTS: int = 10000

    API_PREFIX: str = "/api/v1"

    DOCS_URL: str | None = "/docs"
    OPENAPI_URL: str = "/openapi.json"
    REDOC_URL: str | None = "/redoc"

    ALLOWED_ORIGINS: list[str] = ["*"]
    ALLOWED_METHODS: list[str] = ["*"]
    ALLOWED_HEADERS: list[str] = ["*"]

    LOGGERS: tuple[str, str] = ("uvicorn.asgi", "uvicorn.access")

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        validate_assignment = True
        extra = "allow"

    @property
    def set_app_attributes(self) -> Dict[str, Any]:
        return {
            "title": self.TITLE,
            "version": self.VERSION,
            "debug": self.DEBUG,
            "description": self.DESCRIPTION,
            "docs_url": self.DOCS_URL,
            "openapi_url": self.OPENAPI_URL,
            "redoc_url": self.REDOC_URL,
            "api_prefix": self.API_PREFIX,
        }
