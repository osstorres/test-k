from typing import Annotated

from fastapi import Depends

from app.core.config.logging import logger
from app.core.services.kavak_llm_manager import KavakLLMManager
from app.core.services.memory_manager import get_memory_manager, MemoryManager
from app.domain.agent_kavak.facade import KavakAgentFacade
from app.repository.vector import QdrantVectorRepository


def get_qdrant_repository() -> QdrantVectorRepository:
    """Get or create QdrantVectorRepository singleton instance."""
    try:
        return QdrantVectorRepository.get_instance()
    except RuntimeError as exc:
        logger.error(
            "Failed to initialize QdrantVectorRepository",
            extra={"extra_fields": {"error": str(exc)}},
        )
        raise
    except Exception as exc:
        logger.error(
            "Unexpected error initializing QdrantVectorRepository",
            extra={"extra_fields": {"error": str(exc)}},
            exc_info=True,
        )
        raise


def get_kavak_llm_manager() -> KavakLLMManager:
    """Get or create KavakLLMManager singleton instance."""
    try:
        return KavakLLMManager.get_instance()
    except RuntimeError as exc:
        logger.error(
            "Failed to initialize KavakLLMManager",
            extra={"extra_fields": {"error": str(exc)}},
        )
        raise
    except Exception as exc:
        logger.error(
            "Unexpected error initializing KavakLLMManager",
            extra={"extra_fields": {"error": str(exc)}},
            exc_info=True,
        )
        raise


KavakLLMDep = Annotated[KavakLLMManager, Depends(get_kavak_llm_manager)]
QdrantRepoDep = Annotated[QdrantVectorRepository, Depends(get_qdrant_repository)]
MemoryManagerDep = Annotated[MemoryManager, Depends(get_memory_manager)]


async def get_kavak_facade(
    llm_manager: KavakLLMDep,
    vector_repository: QdrantRepoDep,
    memory_manager: MemoryManagerDep,
) -> KavakAgentFacade:
    return KavakAgentFacade(
        llm_manager=llm_manager,
        vector_repository=vector_repository,
        memory_manager=memory_manager,
    )


KavakFacadeDep = Annotated[KavakAgentFacade, Depends(get_kavak_facade)]
