from pydantic import BaseModel
import decouple


class RedisSettings(BaseModel):
    HOST: str = decouple.config("REDIS_HOST", default="localhost")
    PORT: int = decouple.config("REDIS_PORT", default=6379, cast=int)
    USERNAME: str | None = decouple.config("REDIS_USERNAME", default="default")
    PASSWORD: str | None = decouple.config("REDIS_PASSWORD", default=None)
    DECODE_RESPONSES: bool = decouple.config(
        "REDIS_DECODE_RESPONSES", default=True, cast=bool
    )

    CAG_TTL: int = decouple.config("REDIS_CAG_TTL", default=86400, cast=int)
    CAG_KEY_PREFIX: str = decouple.config(
        "REDIS_CAG_KEY_PREFIX", default="cag:value_prop"
    )
