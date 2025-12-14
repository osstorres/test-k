from typing import Annotated
from fastapi import Depends
from app.core.services.kavak_llm_manager import KavakLLMManager
from app.core.services.memory_manager import get_memory_manager, MemoryManager
from app.persistence.vector.qdrant_repository import QdrantVectorRepository
from app.core.config.logging import logger


def get_qdrant_repository() -> QdrantVectorRepository:
    try:
        return QdrantVectorRepository.get_instance()
    except Exception as exc:
        logger.error(
            "Failed to initialize QdrantVectorRepository",
            extra={"extra_fields": {"error": str(exc)}},
        )
        raise


def get_kavak_llm_manager() -> KavakLLMManager:
    try:
        return KavakLLMManager.get_instance()
    except Exception as exc:
        logger.error(
            "Failed to initialize KavakLLMManager",
            extra={"extra_fields": {"error": str(exc)}},
        )
        raise


KavakLLMDep = Annotated[KavakLLMManager, Depends(get_kavak_llm_manager)]
QdrantRepoDep = Annotated[QdrantVectorRepository, Depends(get_qdrant_repository)]
MemoryManagerDep = Annotated[MemoryManager, Depends(get_memory_manager)]
