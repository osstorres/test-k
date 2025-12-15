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
from .tools import (
    rag_value_prop_tool,
    search_catalog_tool,
    compute_financing_tool,
)

# Constants
DEFAULT_LLM_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 1000
MAX_AGENT_ITERATIONS = 5
MIN_RESPONSE_LENGTH = 10
FUZZY_MATCH_THRESHOLD = 70


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

        self._user_agents: Dict[str, ReActAgent] = {}
        self._user_contexts: Dict[str, Context] = {}

        logger.info(f"Initialized {self.name} agent with ReActAgent")

    def _create_agent(self) -> ReActAgent:
        """Create a new ReActAgent instance with configured tools and prompts."""
        agent = ReActAgent(
            tools=self.tools,
            llm=self.llm,
            max_iterations=MAX_AGENT_ITERATIONS,
            verbose=False,
        )
        agent.update_prompts({"react_header": self._get_system_prompt()})
        return agent

    def _get_user_agent_and_context(
        self, user_id: Optional[str]
    ) -> Tuple[ReActAgent, Context]:
        """Get or create agent and context for a user."""
        if not user_id:
            agent = self._create_agent()
            return agent, Context(agent)

        if user_id not in self._user_agents:
            self._user_agents[user_id] = self._create_agent()
            self._user_contexts[user_id] = Context(self._user_agents[user_id])
            logger.info(f"Created ReActAgent for user: {user_id}")

        return self._user_agents[user_id], self._user_contexts[user_id]

    def _create_tools(self) -> List[FunctionTool]:
        async def rag_value_prop_bound(query: str) -> str:
            result = await rag_value_prop_tool(
                query=query,
                vector_repository=self.vector_repository,
                llm_manager=self.llm_manager,
            )
            return result.answer if hasattr(result, "answer") else str(result)

        async def search_catalog_bound(preferences: str) -> str:
            try:
                prefs_dict = json.loads(preferences)
                prefs = CarPreferences(**prefs_dict)
            except (json.JSONDecodeError, ValueError):
                try:
                    extraction_prompt = f"""Analiza este texto y extrae información sobre el auto mencionado: "{preferences}"

IMPORTANTE: 
- Si menciona una marca Y modelo (ej: "Toyota Corolla", "el Corolla", "toyota corolla", "corolla"), extrae AMBOS: brand y model.
- Si solo menciona marca (ej: "Toyota"), extrae solo brand.
- Si menciona año específico, extrae year_min y year_max con ese año.
- Ignora preguntas sobre características (Bluetooth, CarPlay) - solo extrae marca, modelo, año.

Extrae: marca (brand), modelo (model), año (year_min/year_max si se menciona).

Ejemplos:
- "el toyota corolla tiene bluetooth?" → brand: "Toyota", model: "Corolla"
- "toyota corolla 2020" → brand: "Toyota", model: "Corolla", year_min: 2020, year_max: 2020
- "corolla" → brand: "Toyota", model: "Corolla" (si puedes inferir la marca)

Responde en formato JSON válido."""

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
        prompt_str = """Eres un agente comercial de Kavak en México. Responde de forma directa y concisa.

REGLAS CRÍTICAS:
- Para preguntas sobre Kavak (sedes, servicios, garantías): usa rag_value_prop
- Para CUALQUIER pregunta sobre un auto específico (marca, modelo) o sus características (Bluetooth, CarPlay, dimensiones): SIEMPRE usa search_catalog PRIMERO
- Para financiamiento: usa compute_financing
- NUNCA inventes información sobre características de autos. SIEMPRE busca en el catálogo.
- Si el usuario pregunta "¿el X tiene Y?" o "X tiene bluetooth?", busca ese auto específico usando search_catalog y responde con la información encontrada.
- Responde en español mexicano, máximo 2-3 párrafos

EJEMPLOS DE CUANDO USAR search_catalog:
- "el toyota corolla tiene bluetooth?" → Usa search_catalog con brand: "Toyota", model: "Corolla"
- "corolla tiene carplay?" → Usa search_catalog con brand: "Toyota", model: "Corolla"
- "qué autos toyota tienen?" → Usa search_catalog con brand: "Toyota"
- "dimensiones del corolla" → Usa search_catalog con brand: "Toyota", model: "Corolla"

## Tools

You have access to the following tools:
{tool_desc}

## Output Format

Thought: (breve análisis)
Action: tool name (one of {tool_names})
Action Input: JSON con parámetros

O cuando tengas la respuesta:
Thought: Tengo suficiente información
Answer: [respuesta en español mexicano, concisa]

IMPORTANTE: 
- Sé directo. Usa máximo 3 iteraciones.
- Si la pregunta menciona una marca/modelo o pregunta sobre características, SIEMPRE usa search_catalog primero.
- Si la pregunta es simple (ej: "sedes en Monterrey"), usa UNA herramienta y responde."""
        return PromptTemplate(prompt_str)

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

            if user_id:
                await self.chat_context_repository.initialize()

                chat_context_task = self.chat_context_repository.get_chat_context(
                    str(user_id)
                )
                agent, ctx = self._get_user_agent_and_context(user_id)
                chat_context = await chat_context_task
            else:
                agent, ctx = self._get_user_agent_and_context(user_id)
                chat_context = None

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

            logger.info("[AGENT] ReActAgent completed successfully")

            return {
                "response": verified_response,
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

    def _verify_response(self, response: str, original_query: str) -> str:
        if not response or len(response.strip()) < MIN_RESPONSE_LENGTH:
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
