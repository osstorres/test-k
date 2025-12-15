from __future__ import annotations
from typing import Dict, Any, Optional
from app.core.config.logging import logger
from app.core.config.settings.kavak_config import KavakSettings
from mem0 import Memory


class MemoryManager:
    _instance: Optional[MemoryManager] = None
    _initialized: bool = False

    def __new__(cls) -> MemoryManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            self.config = self._build_config()
            self._initialized = True

        except Exception:
            raise

    def _build_config(self) -> Dict[str, Any]:
        kavak_settings = KavakSettings()

        embedding_model = kavak_settings.mem0.EMBEDDING_MODEL
        vector_size = 1536
        if "large" in embedding_model.lower():
            vector_size = 3072
        elif "ada-002" in embedding_model.lower():
            vector_size = 1536

        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": kavak_settings.mem0.COLLECTION_NAME,
                    "embedding_model_dims": vector_size,
                    "host": kavak_settings.qdrant.HOST,
                    "port": kavak_settings.qdrant.PORT,
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": kavak_settings.mem0.LLM_MODEL,
                    "temperature": 0.7,
                    "api_key": kavak_settings.llm.OPENAI_API_KEY,
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": kavak_settings.mem0.EMBEDDING_MODEL,
                    "api_key": kavak_settings.llm.OPENAI_API_KEY,
                },
            },
            "version": "v1.1",
        }

        if kavak_settings.qdrant.API_KEY:
            config["vector_store"]["config"]["api_key"] = kavak_settings.qdrant.API_KEY

        return config

    async def add_conversation_memory(
        self,
        user_id: str,
        query: str,
        answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            memory = Memory.from_config(self.config)

            messages = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": answer},
            ]

            result = memory.add(messages, user_id=user_id, metadata=metadata or {})

            logger.info(
                f"Added memory for user {user_id}",
                extra={"extra_fields": {"metadata": metadata}},
            )
            return {"success": True, "result": result}

        except Exception as exc:
            logger.error(
                f"Failed to add conversation memory for user {user_id}: {exc}",
                exc_info=True,
            )
            return {"success": False, "error": str(exc)}


_memory_manager_instance: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager_instance
    if _memory_manager_instance is None:
        _memory_manager_instance = MemoryManager()
    return _memory_manager_instance
