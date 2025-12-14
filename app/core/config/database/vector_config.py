from pydantic import BaseModel
import decouple


class VectorDBSettings(BaseModel):
    QDRANT_HOST: str = decouple.config("QDRANT_HOST", default="localhost")
    QDRANT_PORT: int = decouple.config("QDRANT_PORT", default=6333, cast=int)
    QDRANT_GRPC_PORT: int = decouple.config("QDRANT_GRPC_PORT", default=6334, cast=int)
    QDRANT_API_KEY: str | None = decouple.config("QDRANT_API_KEY", default=None)
    QDRANT_USE_TLS: bool = decouple.config("QDRANT_USE_TLS", default=False, cast=bool)

    QDRANT_POOL_MIN_SIZE: int = decouple.config(
        "QDRANT_POOL_MIN_SIZE", default=5, cast=int
    )
    QDRANT_POOL_MAX_SIZE: int = decouple.config(
        "QDRANT_POOL_MAX_SIZE", default=20, cast=int
    )
    QDRANT_POOL_TIMEOUT: int = decouple.config(
        "QDRANT_POOL_TIMEOUT", default=30, cast=int
    )
    QDRANT_MAX_INACTIVE_LIFETIME: int = decouple.config(
        "QDRANT_MAX_INACTIVE_LIFETIME", default=300, cast=int
    )
