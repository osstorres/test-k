import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple

from llama_index.core.agent.workflow import ReActAgent
from llama_index.core.workflow import Context
from llama_index.core.tools import FunctionTool
from llama_index.core import PromptTemplate

from app.core.config.logging import logger
from app.core.services.kavak_llm_manager import KavakLLMManager
from app.core.services.memory_manager import MemoryManager
from app.repository.vector import QdrantVectorRepository
from app.repository.postgres.chat_context_repository import ChatContextRepository
from app.models.agent.chat_interaction import ChatInteractionCreate
from app.models.agent.schemas import CarPreferences
from app.domain.prompts import (
    AGENT_SYSTEM_PROMPT,
    build_car_preferences_extraction_prompt,
)
from .tools import (
    rag_value_prop_tool,
    search_catalog_tool,
    compute_financing_tool,
)

DEFAULT_LLM_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 1000
MAX_AGENT_ITERATIONS = 5
MIN_RESPONSE_LENGTH = 10


class KavakAgentWorkflow:
    name: str = "kavak_agent"
    description: str = (
        "Commercial sales agent for Kavak with RAG, catalog search, and financing"
    )

    def __init__(
        self,
        llm_manager: KavakLLMManager,
        vector_repository: QdrantVectorRepository,
        memory_manager: Optional[MemoryManager] = None,
        chat_context_repository: Optional[ChatContextRepository] = None,
        **kwargs,
    ):
        self.llm_manager = llm_manager
        self.vector_repository = vector_repository
        self.memory_manager = memory_manager
        self.chat_context_repository = (
            chat_context_repository or ChatContextRepository()
        )

        self.tools = self._create_tools()
        self.llm = self.llm_manager.get_llama_index_llm(
            temperature=DEFAULT_LLM_TEMPERATURE, max_tokens=DEFAULT_MAX_TOKENS
        )
        self._agent = self._create_agent()

        logger.info(f"Initialized {self.name} agent with ReActAgent (stateless)")

    def _create_agent(self) -> ReActAgent:
        agent = ReActAgent(
            tools=self.tools,
            llm=self.llm,
            max_iterations=MAX_AGENT_ITERATIONS,
            verbose=False,
        )
        agent.update_prompts({"react_header": self._get_system_prompt()})
        return agent

    def _get_agent_and_context(self) -> Tuple[ReActAgent, Context]:
        ctx = Context(self._agent)
        return self._agent, ctx

    def _create_tools(self) -> List[FunctionTool]:
        # Value prop tool
        async def rag_value_prop_bound(query: str) -> str:
            result = await rag_value_prop_tool(
                query=query,
                vector_repository=self.vector_repository,
                llm_manager=self.llm_manager,
            )
            return result.answer if hasattr(result, "answer") else str(result)

        # Search catalog tool
        async def search_catalog_bound(preferences: str) -> str:
            try:
                prefs_dict = json.loads(preferences)
                prefs = CarPreferences(**prefs_dict)
            except (json.JSONDecodeError, ValueError):
                try:
                    extraction_prompt = build_car_preferences_extraction_prompt(
                        preferences
                    )

                    prefs = await self.llm_manager.complete_structured_text(
                        prompt=extraction_prompt,
                        response_schema=CarPreferences,
                        temperature=0.1,
                        max_tokens=200,
                    )

                    logger.info(
                        f"Extracted preferences from natural language: {prefs.model_dump(exclude_none=True)}"
                    )
                except Exception as exc:
                    logger.warning(
                        f"Error parsing preferences: {exc}, using empty preferences"
                    )
                    prefs = CarPreferences()

            logger.info(
                f"Searching catalog with preferences: {prefs.model_dump(exclude_none=True)}"
            )
            result = await search_catalog_tool(
                preferences=prefs,
                vector_repository=self.vector_repository,
                llm_manager=self.llm_manager,
            )

            logger.info(f"Found {len(result)} cars in catalog search")

            if not result:
                logger.warning(
                    f"No cars found for preferences: {prefs.model_dump(exclude_none=True)}"
                )
                return "No encontré autos que coincidan con tus preferencias. ¿Te gustaría ajustar algún criterio?"

            car_descriptions = []
            for i, car in enumerate(result[:5], 1):
                desc = f"{i}. {car.brand} {car.model} {car.year}"
                if car.version:
                    desc += f" - Versión: {car.version}"
                desc += f" - Precio: ${car.price:,.0f} MXN"
                if car.mileage:
                    desc += f" - Kilometraje: {car.mileage:,} km"

                features_list = []
                if car.bluetooth is not None:
                    if car.bluetooth:
                        features_list.append("SÍ tiene Bluetooth")
                    else:
                        features_list.append("NO tiene Bluetooth")
                if car.car_play is not None:
                    if car.car_play:
                        features_list.append("SÍ tiene Apple CarPlay")
                    else:
                        features_list.append("NO tiene Apple CarPlay")

                if features_list:
                    desc += f" - Características: {', '.join(features_list)}"

                dims = []
                if car.length:
                    dims.append(f"Largo: {car.length:.0f} mm")
                if car.width:
                    dims.append(f"Ancho: {car.width:.0f} mm")
                if car.height:
                    dims.append(f"Altura: {car.height:.0f} mm")
                if dims:
                    desc += f" - Dimensiones: {', '.join(dims)}"

                car_descriptions.append(desc)

            return "\n".join(car_descriptions)

        tools = [
            FunctionTool.from_defaults(
                fn=rag_value_prop_bound,
                name="rag_value_prop",
                description="Responde preguntas sobre la propuesta de valor de Kavak usando RAG. Úsala para preguntas sobre Kavak, servicios, ubicaciones, sedes, garantías, financiamiento, proceso de compra, etc. Retorna respuesta con citas de fuentes.",
            ),
            FunctionTool.from_defaults(
                fn=search_catalog_bound,
                name="search_catalog",
                description="Busca en el catálogo de autos usando búsqueda semántica. Úsala SIEMPRE cuando el usuario pregunte sobre un auto específico (marca, modelo) o sus características (Bluetooth, CarPlay, dimensiones, etc.). Toma preferencias del usuario (marca, modelo, presupuesto, año, transmisión, etc.) en formato JSON o texto natural. Retorna lista de autos con TODA su información: marca, modelo, año, precio, kilometraje, versión, características (Bluetooth, CarPlay) y dimensiones. SOLO recomienda autos devueltos por esta herramienta.",
            ),
            FunctionTool.from_defaults(
                fn=compute_financing_tool,
                name="compute_financing",
                description="Calcula un plan de financiamiento. Parámetros: price (precio del auto en MXN), down_payment (enganche en MXN), years (plazo en años, 3-6). Usa tasa de interés anual del 10%. Retorna pago mensual, interés total y monto total.",
            ),
        ]
        return tools

    def _get_system_prompt(self) -> PromptTemplate:
        return PromptTemplate(AGENT_SYSTEM_PROMPT)

    async def process_query(
        self,
        query: str,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            logger.info("[AGENT] Processing query with ReActAgent")
            logger.info(f"User ID: {user_id}")
            logger.info("Architecture: Agent-based (automatic tool selection)")

            agent, ctx = self._get_agent_and_context()

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

            handler = agent.run(query_to_use, ctx=ctx)
            response = await handler

            response_text = str(response)
            response_text = response_text.strip()

            if user_id:
                asyncio.create_task(
                    self.chat_context_repository.add_interaction(
                        ChatInteractionCreate(
                            user_id=str(user_id),
                            query=query,
                            response=response_text,
                        )
                    )
                )

            logger.info("[AGENT] ReActAgent completed successfully")

            return {
                "response": response_text,
                "user_id": user_id,
                "agent": self.name,
                "provider": self.llm_manager.settings.llm.PROVIDER,
                "model": self.llm_manager.settings.llm.MODEL,
            }

        except Exception as exc:
            logger.error(
                f"[AGENT] Error processing query with ReActAgent: {exc}", exc_info=True
            )
            raise
