from pydantic import BaseModel
import decouple


class KavakLLMSettings(BaseModel):
    PROVIDER: str = decouple.config("KAVAK_LLM_PROVIDER", default="openai")
    MODEL: str = decouple.config("KAVAK_LLM_MODEL", default="gpt-4.1")

    OPENAI_API_KEY: str | None = decouple.config("OPENAI_API_KEY", default=None)


class KavakQdrantSettings(BaseModel):
    HOST: str = decouple.config("QDRANT_HOST", default="localhost")
    PORT: int = decouple.config("QDRANT_PORT", default=6333, cast=int)
    GRPC_PORT: int = decouple.config("QDRANT_GRPC_PORT", default=6334, cast=int)
    API_KEY: str | None = decouple.config("QDRANT_API_KEY", default=None)
    USE_TLS: bool = decouple.config("QDRANT_USE_TLS", default=True, cast=bool)

    VALUE_PROP_COLLECTION: str = decouple.config(
        "KAVAK_QDRANT_VALUE_PROP_COLLECTION", default="kavak_value_prop"
    )
    CATALOG_COLLECTION: str = decouple.config(
        "KAVAK_QDRANT_CATALOG_COLLECTION", default="kavak_catalog"
    )


class KavakMem0Settings(BaseModel):
    COLLECTION_NAME: str = decouple.config(
        "KAVAK_MEM0_COLLECTION_NAME", default="kavak_user_memory"
    )
    LLM_MODEL: str = decouple.config("KAVAK_MEM0_LLM_MODEL", default="gpt-4.1")
    EMBEDDING_MODEL: str = decouple.config(
        "KAVAK_MEM0_EMBEDDING_MODEL", default="text-embedding-3-small"
    )


class KavakTwilioSettings(BaseModel):
    ACCOUNT_SID: str = decouple.config("TWILIO_ACCOUNT_SID", default="")
    AUTH_TOKEN: str = decouple.config("TWILIO_AUTH_TOKEN", default="")

    WHATSAPP_FROM: str = decouple.config(
        "TWILIO_WHATSAPP_FROM", default="whatsapp:+00000000000"
    )

    WEBHOOK_URL: str = decouple.config("TWILIO_WEBHOOK_URL", default="")
    WEBHOOK_SECRET: str | None = decouple.config("TWILIO_WEBHOOK_SECRET", default=None)
    SANDBOX_CODE: str | None = decouple.config("TWILIO_SANDBOX_CODE", default=None)


class KavakSettings(BaseModel):
    llm: KavakLLMSettings = KavakLLMSettings()
    qdrant: KavakQdrantSettings = KavakQdrantSettings()
    mem0: KavakMem0Settings = KavakMem0Settings()
    twilio: KavakTwilioSettings = KavakTwilioSettings()
