
from functools import lru_cache
from contextlib import asynccontextmanager
import decouple
from app.core.config.logging import logger
from app.core.config.settings.environments import (
    Environment,
    DevSettings,
    LocalSettings,
    ProdSettings,
)
from app.core.config.settings.base_config import ApplicationSettings


class Singleton(type):
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class SettingsFactory:
    def __init__(self, environment: str):
        self.environment = environment

    def __call__(self) -> ApplicationSettings:
        """Create settings instance based on environment."""
        if self.environment == Environment.DEVELOPMENT.value:
            return DevSettings()
        if self.environment == Environment.LOCAL.value:
            return LocalSettings()
        # Default to PRODUCTION
        return ProdSettings()


@lru_cache()
def get_settings() -> ApplicationSettings:
    env = decouple.config("ENVIRONMENT", default=Environment.PRODUCTION.value, cast=str)
    return SettingsFactory(environment=env)()


@asynccontextmanager
async def lifespan(app):
    try:
        yield
    finally:
        logger.info("Shutting down application...")
        try:
            pass
        except Exception:
            pass

settings: ApplicationSettings = get_settings()
