from typing import Optional, Union
from app.core.config.logging import logger
from app.core.services.kavak_llm_manager import KavakLLMManager
from app.core.services.memory_manager import MemoryManager
from app.persistence.vector.qdrant_repository import QdrantVectorRepository
from .kavak_agent import KavakAgentWorkflow
from app.domain.deterministic_kavak.main import DeterministicKavakAgent

USE_AGENT: bool = True


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
        self.use_agent = USE_AGENT

        logger.info(f"Kavak Agent Factory initialized (USE_AGENT={self.use_agent})")

    async def get_workflow(self) -> Union[KavakAgentWorkflow, DeterministicKavakAgent]:
        if self.use_agent:
            agent = KavakAgentWorkflow(
                llm_manager=self.llm_manager,
                vector_repository=self.vector_repository,
                memory_manager=self.memory_manager,
            )
            logger.info(
                "[FACTORY] Using ReActAgent workflow (multi-turn, tool-based reasoning)"
            )
            return agent
        else:
            agent = DeterministicKavakAgent(
                llm_manager=self.llm_manager,
                vector_repository=self.vector_repository,
                memory_manager=self.memory_manager,
            )
            logger.info(
                "[FACTORY] Using Deterministic Workflow (fast-path, agent-lite architecture)"
            )
            return agent
