"""
Kavak Agent Facade - Main entry point for Kavak agent operations

Simple facade for Kavak commercial sales agent using LlamaIndex workflows.
"""

from typing import Dict, Any, Optional
from app.core.config.logging import logger
from app.core.services.kavak_llm_manager import KavakLLMManager
from app.core.services.memory_manager import MemoryManager
from app.persistence.vector.qdrant_repository import QdrantVectorRepository
from .workflows.factory import KavakAgentFactory


class KavakAgentFacade:
    """Facade for Kavak agent operations."""

    def __init__(
        self,
        llm_manager: KavakLLMManager,
        vector_repository: QdrantVectorRepository,
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.llm_manager = llm_manager
        self.vector_repository = vector_repository
        self.memory_manager = memory_manager
        self.workflow_factory = KavakAgentFactory(
            llm_manager=llm_manager,
            vector_repository=vector_repository,
            memory_manager=memory_manager,
        )

    async def process_query(
        self,
        query: str,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Process a query using the Kavak agent (uses pre-configured settings)."""
        try:
            logger.info(f"Processing query with Kavak agent for user: {user_id}")

            workflow = await self.workflow_factory.get_workflow()

            result = await workflow.process_query(
                query=query,
                user_id=user_id,
                **kwargs,
            )

            return result

        except Exception as exc:
            logger.error(f"Error processing query with Kavak agent: {exc}")
            raise
