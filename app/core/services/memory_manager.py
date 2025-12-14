from __future__ import annotations
from typing import Dict, Any, List, Optional
from app.core.config.logging import logger
from app.core.config.settings.kavak_config import KavakSettings


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
            from mem0 import Memory

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
            }

            if kavak_settings.qdrant.API_KEY:
                config["vector_store"]["config"]["api_key"] = (
                    kavak_settings.qdrant.API_KEY
                )

            self.memory = Memory.from_config(config)
            self._initialized = True

            logger.info("Memory Manager initialized successfully")

        except ImportError as exc:
            logger.error("Mem0 library not installed. Install with: pip install mem0ai")
            raise ImportError("Mem0 library is required for memory management") from exc
        except Exception as exc:
            logger.error(f"Failed to initialize Memory Manager: {exc}")
            raise

    async def add_conversation_memory(
        self,
        user_id: str,
        query: str,
        answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            messages = [
                {"role": "user", "content": query},
                {"role": "assistant", "content": answer},
            ]

            result = self.memory.add(messages, user_id=user_id, metadata=metadata or {})
            logger.info(f"Added memory for user {user_id}")
            return {"success": True, "result": result}

        except Exception as exc:
            logger.error(f"Failed to add conversation memory: {exc}", exc_info=True)
            return {"success": False, "error": str(exc)}

    async def get_relevant_memories(
        self, user_id: str, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        try:
            memories = self.memory.search(query=query, user_id=user_id, limit=limit)
            return memories or []
        except Exception as exc:
            logger.error(f"Failed to retrieve memories: {exc}", exc_info=True)
            return []


_memory_manager_instance: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    global _memory_manager_instance
    if _memory_manager_instance is None:
        _memory_manager_instance = MemoryManager()
    return _memory_manager_instance
