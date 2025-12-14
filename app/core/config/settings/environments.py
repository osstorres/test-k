from app.core.config.settings.types_config import Environment
from app.core.config.settings.base_config import ApplicationSettings


class LocalSettings(ApplicationSettings):
    DESCRIPTION: str | None = "Local Environment."
    DEBUG: bool = True
    ENVIRONMENT: Environment = Environment.LOCAL


class DevSettings(ApplicationSettings):
    DESCRIPTION: str | None = "Development Environment."
    DEBUG: bool = True
    ENVIRONMENT: Environment = Environment.DEVELOPMENT


class ProdSettings(ApplicationSettings):
    DESCRIPTION: str | None = "Production Environment."
    ENVIRONMENT: Environment = Environment.PRODUCTION
