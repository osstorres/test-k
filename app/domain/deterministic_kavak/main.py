from typing import Dict, Any, Optional
from app.core.config.logging import logger
from app.core.services.kavak_llm_manager import KavakLLMManager
from app.core.services.memory_manager import MemoryManager
from app.persistence.vector.qdrant_repository import QdrantVectorRepository
from app.persistence.chat_context_repository import ChatContextRepository
from app.models.chat_interaction import ChatInteractionCreate
from .workflow import DeterministicKavakWorkflow
import asyncio


class DeterministicKavakAgent:
    name: str = "deterministic_kavak_agent"
    description: str = (
        "Deterministic step-based workflow for Kavak commercial sales agent"
    )

    def __init__(
        self,
        llm_manager: KavakLLMManager,
        vector_repository: QdrantVectorRepository,
        memory_manager: Optional[MemoryManager] = None,
        chat_context_repository: Optional[ChatContextRepository] = None,
        timeout: int = 60,
        verbose: bool = False,
        **kwargs,
    ):
        self.llm_manager = llm_manager
        self.vector_repository = vector_repository
        self.memory_manager = memory_manager
        self.chat_context_repository = (
            chat_context_repository or ChatContextRepository()
        )

        self.workflow = DeterministicKavakWorkflow(
            llm_manager=llm_manager,
            vector_repository=vector_repository,
            memory_manager=memory_manager,
            chat_context_repository=self.chat_context_repository,
            timeout=timeout,
            verbose=verbose,
        )

        logger.info(f"Initialized {self.name} with deterministic workflow")
        logger.info(
            "[WORKFLOW] Deterministic Kavak Agent initialized (agent-lite architecture)"
        )

    async def process_query(
        self,
        query: str,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            logger.info("[WORKFLOW] Processing query with Deterministic Workflow")

            chat_context = None
            if user_id:
                await self.chat_context_repository.initialize()
                chat_context = await self.chat_context_repository.get_chat_context(
                    str(user_id)
                )

            query_to_use = query
            if chat_context and chat_context.interactions:
                context_string = chat_context.to_context_string()
                if context_string:
                    logger.info(
                        f"Retrieved {len(chat_context.interactions)} previous interactions from chat context"
                    )
                    query_to_use = f"{context_string}\n\n## Consulta Actual\n{query}"

            result = await self.workflow.run(query=query_to_use, user_id=user_id)
            response_text = (
                str(result) if result else "Lo siento, no pude generar una respuesta."
            )
            response_text = response_text.strip()
            verified_response = self._verify_response(response_text, query)

            if user_id:
                asyncio.create_task(
                    self.chat_context_repository.add_interaction(
                        ChatInteractionCreate(
                            user_id=str(user_id),
                            query=query,
                            response=verified_response,
                        )
                    )
                )

            logger.info("[WORKFLOW] Deterministic Workflow completed successfully")

            return {
                "response": verified_response,
                "user_id": user_id,
                "agent": self.name,
                "provider": self.llm_manager.settings.llm.PROVIDER,
                "model": self.llm_manager.settings.llm.MODEL,
            }

        except Exception as exc:
            logger.error(
                f"[WORKFLOW] Error processing query with deterministic workflow: {exc}",
                exc_info=True,
            )
            raise

    def _verify_response(self, response: str, original_query: str) -> str:
        if not response or len(response.strip()) < 10:
            return "Lo siento, no pude generar una respuesta adecuada. ¿Podrías reformular tu pregunta?"

        hallucination_indicators = [
            "no tengo acceso a",
            "no puedo acceder a",
            "no tengo información sobre",
        ]

        response_lower = response.lower()
        query_lower = original_query.lower()

        if any(indicator in response_lower for indicator in hallucination_indicators):
            if any(
                word in query_lower
                for word in ["kavak", "qué es", "quienes son", "información"]
            ):
                logger.warning(
                    f"Response indicates lack of info for basic Kavak query: {original_query[:50]}"
                )

        spanish_words = ["el", "la", "de", "que", "y", "en", "un", "es", "para", "con"]
        has_spanish = any(word in response_lower for word in spanish_words)

        if not has_spanish and len(response) > 50:
            logger.warning(f"Response might not be in Spanish: {response[:100]}")

        return response
