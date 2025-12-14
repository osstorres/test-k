from pydantic import BaseModel
import decouple


class PostgresSettings(BaseModel):
    POSTGRES_HOST: str = decouple.config("POSTGRES_HOST", default="localhost")
    POSTGRES_PORT: int = decouple.config("POSTGRES_PORT", default=5432, cast=int)
    POSTGRES_DB: str = decouple.config("POSTGRES_DB", default="kavak_chat")
    POSTGRES_USER: str = decouple.config("POSTGRES_USER", default="postgres")
    POSTGRES_PASSWORD: str = decouple.config("POSTGRES_PASSWORD", default="postgres")

    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_MAX_OVERFLOW: int = 10

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
