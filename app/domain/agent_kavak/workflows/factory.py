from typing import Optional
from app.core.config.logging import logger
from app.core.services.kavak_llm_manager import KavakLLMManager
from app.core.services.memory_manager import MemoryManager
from app.repository.vector import QdrantVectorRepository
from .kavak_agent import KavakAgentWorkflow


class KavakAgentFactory:
    def __init__(
        self,
        llm_manager: KavakLLMManager,
        vector_repository: QdrantVectorRepository,
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.llm_manager = llm_manager
        self.vector_repository = vector_repository
        self.memory_manager = memory_manager

        logger.info("Kavak Agent Factory initialized")

    async def get_workflow(self) -> KavakAgentWorkflow:
        agent = KavakAgentWorkflow(
            llm_manager=self.llm_manager,
            vector_repository=self.vector_repository,
            memory_manager=self.memory_manager,
        )
        logger.info(
            "[FACTORY] Using ReActAgent workflow (multi-turn, tool-based reasoning)"
        )
        return agent
