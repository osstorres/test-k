from typing import Dict, Any, Optional
from llama_index.core.workflow import Workflow, step
from llama_index.core.workflow import StartEvent, StopEvent
from app.core.config.logging import logger
from app.core.services.kavak_llm_manager import KavakLLMManager
from app.core.services.memory_manager import MemoryManager
from app.persistence.vector.qdrant_repository import QdrantVectorRepository
from app.persistence.chat_context_repository import ChatContextRepository
from app.domain.agent_kavak.workflows.schemas import (
    UserIntent,
    CarPreferences,
)
import re
from .tools import compute_financing_tool, retrieve_context
from .events import RoutingEvent


SYSTEM_PROMPT = """Eres un asesor comercial de Kavak en México.

Tu objetivo es ayudar a los usuarios a encontrar autos del catálogo y entender los servicios de Kavak de forma clara, cercana y humana, como lo haría una persona real en un chat de ventas.

REGLAS ESTRICTAS (NO NEGOCIABLES)

1. Usa únicamente la información que se te proporcione en el contexto (catálogo y contenidos de Kavak).

2. No inventes autos, precios, versiones, características, ubicaciones ni políticas.

3. Si un dato no está disponible en el catálogo, dilo explícitamente.

4. Si el usuario pide un modelo que no existe, sugiere únicamente opciones reales del catálogo.

5. Nunca prometas información financiera fuera de:
   - precio del auto
   - enganche
   - tasa anual fija del 10%
   - plazo de 3 a 6 años

6. Si no puedes responder con certeza, dilo de forma clara y amable.

FINANCIAMIENTO

- Calcula mensualidades solo con precio, enganche, tasa anual del 10% y plazo (3–6 años).

- Presenta los montos como aproximados.

- No menciones bancos, score, CAT, seguros ni comisiones.

ESTILO DE CONVERSACIÓN

- Sé amable, claro y natural.

- Evita lenguaje robótico o corporativo.

- Explica como una persona real.

- Haz preguntas breves para avanzar la conversación.

- Mantén respuestas concisas (máximo 2-3 párrafos para chat/WhatsApp).

FORMATO

- Cuando recomiendes autos, incluye solo:
  marca, modelo, año, precio, kilometraje, versión y características disponibles (solo si están en el contexto).

- Termina normalmente con una pregunta para continuar el flujo."""


class DeterministicKavakWorkflow(Workflow):
    def __init__(
        self,
        llm_manager: KavakLLMManager,
        vector_repository: QdrantVectorRepository,
        memory_manager: Optional[MemoryManager] = None,
        chat_context_repository: Optional[ChatContextRepository] = None,
        timeout: int = 60,
        verbose: bool = False,
    ):
        super().__init__(timeout=timeout, verbose=verbose)
        self.llm_manager = llm_manager
        self.vector_repository = vector_repository
        self.memory_manager = memory_manager
        self.chat_context_repository = chat_context_repository
        self.llm = self.llm_manager.get_llama_index_llm(
            temperature=0.7, max_tokens=1500
        )

    @step
    async def extract_intent_and_preferences(self, ev: StartEvent) -> RoutingEvent:
        query = ev.query if hasattr(ev, "query") else str(ev)

        has_previous_context = "## Contexto de Conversaciones Previas" in query

        logger.info(
            f"[Step 1] Extracting intent and preferences from query: {query[:100]}..."
        )
        if has_previous_context:
            logger.info("   📝 Query includes context from previous conversations")

        try:
            intent_prompt = f"""Analiza la siguiente consulta del usuario y determina:
1. La intención principal: value_prop (preguntas sobre Kavak), recommend (búsqueda de autos), finance (financiamiento), o other (conversación general)
2. El nivel de complejidad: simple (una sola intención clara) o complex (múltiples intenciones mezcladas)
3. Las preferencias o filtros relevantes si la intención es recommend o finance

Consulta: "{query}"

Responde con la intención, nivel de complejidad y su nivel de confianza (0.0 a 1.0)."""

            intent_result = await self.llm_manager.complete_structured_text(
                prompt=intent_prompt,
                response_schema=UserIntent,
                temperature=0.2,
                max_tokens=200,
            )

            intent = intent_result.intent
            confidence = intent_result.confidence

            complexity = "simple"
            query_lower = query.lower()
            topic_count = sum(
                [
                    1 if word in query_lower else 0
                    for word in [
                        "auto",
                        "coche",
                        "carro",
                        "financiamiento",
                        "financiar",
                        "kavak",
                        "sede",
                        "garantía",
                    ]
                ]
            )
            if topic_count >= 3 or len(query.split()) > 15:
                complexity = "complex"

            logger.info(f"[COMPLEXITY] Detected complexity: {complexity.upper()}")
            logger.info(f"Intent: {intent} (confidence: {confidence:.2f})")
            logger.info(
                f"Topic count: {topic_count}, Query length: {len(query.split())} words"
            )

            preferences = None
            if intent in ["recommend", "finance"]:
                try:
                    if intent == "recommend":
                        preferences_prompt = f"""Extrae las preferencias de auto de esta consulta: "{query}"

Extrae la siguiente información:
- brand (marca): Si el usuario menciona una marca (ej: "kia", "toyota", "honda"), extrae el nombre de la marca en su forma más común (ej: "Kia", "Toyota", "Honda"). Si menciona "kia" o "KIA", extrae "Kia".
- model (modelo): Modelo específico si se menciona
- budget_max: Presupuesto máximo si se menciona
- year_min/year_max: Rango de años si se menciona
- transmission: Tipo de transmisión si se menciona
- fuel: Tipo de combustible si se menciona
- city: Ciudad si se menciona
- mileage_max: Kilometraje máximo si se menciona

IMPORTANTE: 
- Si el usuario solo menciona una marca (ej: "dame opciones de kia"), extrae la marca normalizada (ej: "Kia").
- Para marcas comunes, usa la capitalización estándar: Kia, Toyota, Honda, Nissan, Volkswagen, Ford, Chevrolet, etc.
- Si no está seguro de una marca, usa la forma que más probablemente esté en el catálogo.
- Si algún campo no está mencionado, déjalo como None."""

                        prefs_result = await self.llm_manager.complete_structured_text(
                            prompt=preferences_prompt,
                            response_schema=CarPreferences,
                            temperature=0.2,
                            max_tokens=300,
                        )

                        preferences = prefs_result.model_dump(exclude_none=True)

                    elif intent == "finance":
                        preferences = {}

                except Exception as exc:
                    logger.warning(
                        f"Error extracting preferences: {exc}, continuing without preferences"
                    )
                    preferences = None

            logger.info("[STEP 1] Intent extraction completed")
            logger.info(f"Intent: {intent}")
            logger.info(f"Complexity: {complexity}")
            logger.info(f"Confidence: {confidence:.2f}")
            logger.info(f"Preferences extracted: {bool(preferences)}")

            return RoutingEvent(
                intent=intent,
                confidence=confidence,
                preferences=preferences,
                query=query,
                complexity=complexity,
            )

        except Exception as exc:
            logger.error(
                f"Error in extract_intent_and_preferences: {exc}", exc_info=True
            )
            return RoutingEvent(
                intent="other",
                confidence=0.5,
                preferences=None,
                query=query,
                complexity="simple",
            )

    @step
    async def route_and_process(self, ev: RoutingEvent) -> StopEvent:
        logger.info("[ROUTING] Routing to handler")
        logger.info(f"Intent: {ev.intent}")
        logger.info(f"Complexity: {ev.complexity.upper()}")

        try:
            if ev.complexity == "simple":
                logger.info(
                    "[ROUTING] Using FAST-PATH (single-pass, optimized for speed)"
                )

                return await self._fast_path_process(ev)
            else:
                logger.info(
                    "[ROUTING] Using EXTENDED FAST-PATH (complex query handling)"
                )
                return await self._fast_path_process(ev, extended_context=True)

        except Exception:
            return StopEvent(
                result="Lo siento, ocurrió un error al procesar tu consulta. ¿Podrías intentar de nuevo?"
            )

    async def _fast_path_process(
        self,
        ev: RoutingEvent,
        extended_context: bool = False,
    ) -> StopEvent:
        path_type = "EXTENDED FAST-PATH" if extended_context else "FAST-PATH"
        logger.info(f"Handler: {ev.intent.upper()} ({path_type})")

        if ev.intent == "value_prop":
            logger.info(
                "[HANDLER] Value Prop - Retrieving value proposition context..."
            )

            context_result = await retrieve_context(
                query=ev.query,
                preferences=None,
                vector_repository=self.vector_repository,
                llm_manager=self.llm_manager,
                value_prop_top_k=3,
            )

            value_prop_chunks = context_result.get("value_prop_results", [])

            if not value_prop_chunks:
                response = "Lo siento, no encontré información relevante sobre ese tema. ¿Podrías reformular tu pregunta?"
            else:
                context_text = "\n\n".join(
                    [chunk.get("text", "") for chunk in value_prop_chunks]
                )

                prompt = f"""{SYSTEM_PROMPT}

## Contexto sobre Kavak (usa SOLO esta información):

{context_text}

## Pregunta del usuario:

{ev.query}

## Instrucciones:

Responde la pregunta del usuario usando ÚNICAMENTE la información del contexto proporcionado.
Si la información no está en el contexto, di explícitamente que no tienes esa información.
Responde de forma amigable, concisa y natural (máximo 2-3 párrafos).
Termina con una pregunta para continuar la conversación.

Respuesta:"""

                response = await self.llm_manager.complete_text(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=400,
                )
                response = response.strip()

            return StopEvent(result=response)

        elif ev.intent == "recommend":
            prefs_dict = ev.preferences or {}
            preferences = CarPreferences(**prefs_dict)

            context_result = await retrieve_context(
                query=ev.query,
                preferences=preferences,
                vector_repository=self.vector_repository,
                llm_manager=self.llm_manager,
                catalog_top_k=5,
                value_prop_top_k=0,
            )

            catalog_results = context_result.get("catalog_results", [])

            if not catalog_results:
                brand_name = (
                    preferences.brand
                    if preferences
                    and hasattr(preferences, "brand")
                    and preferences.brand
                    else None
                )
                if brand_name and not (
                    preferences.budget_max
                    or preferences.year_min
                    or preferences.year_max
                ):
                    fallback_prefs = CarPreferences()
                    fallback_result = await retrieve_context(
                        query=ev.query,
                        preferences=fallback_prefs,
                        vector_repository=self.vector_repository,
                        llm_manager=self.llm_manager,
                        catalog_top_k=10,
                    )
                    fallback_cars = fallback_result.get("catalog_results", [])

                    brand_lower = brand_name.lower().strip()
                    filtered_fallback = [
                        car
                        for car in fallback_cars
                        if car.get("brand", "").lower().strip() == brand_lower
                    ]

                    if filtered_fallback:
                        catalog_results = filtered_fallback[:5]

                if not catalog_results:
                    brand_msg = brand_name if brand_name else "esas características"
                    response = f"No encontré autos de {brand_msg} en nuestro catálogo actual. ¿Te gustaría especificar algún modelo, año, o presupuesto? Esto me ayudaría a encontrar mejores opciones para ti."
            else:
                cars_text = []
                for i, car_dict in enumerate(catalog_results[:5], 1):
                    brand = car_dict.get("brand", "")
                    model = car_dict.get("model", "")
                    year = car_dict.get("year", "")
                    price = car_dict.get("price", 0)
                    mileage = car_dict.get("mileage", 0)
                    version = car_dict.get("version", "")
                    bluetooth = car_dict.get("bluetooth", False)
                    car_play = car_dict.get("car_play", False)
                    length = car_dict.get("length")
                    width = car_dict.get("width")
                    height = car_dict.get("height")

                    car_desc = f"{i}. {brand} {model} {year}"
                    if version:
                        car_desc += f" ({version})"
                    car_desc += f" - ${price:,.0f} MXN"
                    if mileage:
                        car_desc += f" - {mileage:,} km"

                    features = []
                    if bluetooth:
                        features.append("Bluetooth")
                    if car_play:
                        features.append("Apple CarPlay")
                    if features:
                        car_desc += f" - Características: {', '.join(features)}"

                    dims = []
                    if length:
                        dims.append(f"Largo: {length:.0f} mm")
                    if width:
                        dims.append(f"Ancho: {width:.0f} mm")
                    if height:
                        dims.append(f"Altura: {height:.0f} mm")
                    if dims:
                        car_desc += f" - Dimensiones: {', '.join(dims)}"

                    cars_text.append(car_desc)

                cars_list = "\n".join(cars_text)

                prompt = f"""{SYSTEM_PROMPT}

## Autos encontrados en el catálogo (recomienda SOLO estos):

{cars_list}

## Consulta del usuario:

{ev.query}

## Instrucciones:

Presenta estos autos de forma amigable y natural. Menciona TODA la información disponible:
- Marca, modelo, año, versión
- Precio y kilometraje
- Características: Bluetooth, Apple CarPlay (cuando estén disponibles)
- Dimensiones: largo, ancho, altura (cuando estén disponibles)

Si un auto tiene Bluetooth o CarPlay, MENCIONALO explícitamente en tu respuesta.
Si el usuario pregunta sobre dimensiones o características específicas, usa la información proporcionada.
Si el usuario mencionó una marca/modelo específica y no aparece en los resultados, menciona que encontraste opciones similares.
Termina con una pregunta para continuar (ej: "¿Te gustaría más información sobre alguno de estos autos o calcular el financiamiento?").

Respuesta:"""

                response = await self.llm_manager.complete_text(
                    prompt=prompt,
                    temperature=0.5,
                    max_tokens=300,
                )
                response = response.strip()

            return StopEvent(result=response)

        elif ev.intent == "finance":
            prefs = ev.preferences or {}
            price = prefs.get("price")
            down_payment = prefs.get("down_payment", 0.0)
            years = prefs.get("years", 3)

            original_query = ev.query
            if not price and "## Contexto de Conversaciones Previas" in original_query:
                car_info = await self._extract_car_info_from_context(
                    original_query, info_needed="all"
                )
                if car_info:
                    price = car_info.get("budget_max")
                    if car_info.get("brand"):
                        prefs["brand"] = car_info["brand"]
                    if car_info.get("model"):
                        prefs["model"] = car_info["model"]
                    if car_info.get("year_min") or car_info.get("year_max"):
                        if car_info.get("year_min"):
                            prefs["year_min"] = car_info["year_min"]
                        if car_info.get("year_max"):
                            prefs["year_max"] = car_info["year_max"]

            if not price:
                try:
                    extract_price_prompt = f"""De la siguiente consulta, extrae el precio del auto en MXN (solo el número, sin comas ni puntos).

Consulta: "{ev.query}"

Si hay un precio mencionado, responde SOLO con el número. Si no hay precio, responde "NO_PRICE"."""
                    price_text = await self.llm_manager.complete_text(
                        prompt=extract_price_prompt,
                        temperature=0.1,
                        max_tokens=50,
                    )
                    price_text = price_text.strip()
                    if price_text and price_text != "NO_PRICE":
                        numbers = re.findall(
                            r"\d+", price_text.replace(",", "").replace(".", "")
                        )
                        if numbers:
                            price = float("".join(numbers))
                except Exception as exc:
                    logger.warning(f"Error extracting price: {exc}")

            if not price:
                response = "No se pudo determinar el precio del auto. Por favor, proporciona el precio del auto para calcular el financiamiento."
                return StopEvent(result=response)

            if years < 3:
                years = 3
            elif years > 6:
                years = 6

            interest_rate = 0.10
            plan = await compute_financing_tool(
                price=float(price),
                down_payment=float(down_payment),
                years=int(years),
                interest_rate=interest_rate,
            )

            user_query = ev.query
            if "## Consulta Actual\n" in user_query:
                user_query = user_query.split("## Consulta Actual\n")[-1]

            prompt = f"""{SYSTEM_PROMPT}

## Plan de financiamiento calculado:

- Pago mensual: ${plan.monthly_payment:,.2f} MXN
- Plazo: {plan.term_years} años ({plan.term_months} meses)
- Interés total: ${plan.total_interest:,.2f} MXN
- Total a pagar: ${plan.total_amount:,.2f} MXN
- Tasa de interés: {plan.interest_rate * 100:.1f}% anual
- Precio del auto: ${float(price):,.2f} MXN
- Enganche: ${plan.total_amount - plan.principal - plan.total_interest:,.2f} MXN

## Consulta del usuario:

{user_query}

## Instrucciones:

Presenta el plan de financiamiento de forma clara y amigable para el auto mencionado anteriormente.
Si el usuario dijo "ese auto" o similar, confirma que es para el auto que mencionamos antes.
Menciona que los montos son aproximados.
No menciones bancos, score, CAT, seguros ni comisiones.
Termina con una pregunta para continuar.

Respuesta:"""

            response = await self.llm_manager.complete_text(
                prompt=prompt,
                temperature=0.4,
                max_tokens=250,
            )
            response = response.strip()

            return StopEvent(result=response)

        else:
            prompt = f"""{SYSTEM_PROMPT}

## Consulta del usuario:

{ev.query}

## Instrucciones:

Responde de manera amigable y profesional. Si la consulta está relacionada con autos o Kavak, proporciona información útil. 
Si no está relacionada, responde de manera educada indicando que puedes ayudar con preguntas sobre Kavak, catálogo de autos, o financiamiento.
Responde en español mexicano, de manera concisa (máximo 2-3 párrafos).

Respuesta:"""

            response = await self.llm_manager.complete_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=300,
            )

            return StopEvent(result=response.strip())

    async def _extract_car_info_from_context(
        self, query_with_context: str, info_needed: str = "price"
    ) -> Optional[Dict[str, Any]]:
        try:
            if "## Contexto de Conversaciones Previas" not in query_with_context:
                return None

            context_parts = query_with_context.split(
                "## Contexto de Conversaciones Previas\n"
            )
            if len(context_parts) < 2:
                return None

            context_and_query = context_parts[1]
            if "## Consulta Actual\n" in context_and_query:
                context_text = context_and_query.split("## Consulta Actual\n")[
                    0
                ].strip()
                current_query = context_and_query.split("## Consulta Actual\n")[
                    1
                ].strip()
            else:
                context_text = context_and_query.strip()
                current_query = query_with_context

            from app.domain.agent_kavak.workflows.schemas import CarPreferences

            extraction_prompt = f"""Analiza el contexto de conversaciones previas y la consulta actual para extraer información sobre el auto mencionado.

## Contexto de Conversaciones Previas:

{context_text}

## Consulta Actual:

{current_query}

La consulta actual hace referencia a un auto mencionado anteriormente (usa palabras como "ese", "ese auto", "el anterior", etc.).

Extrae la siguiente información del contexto:
- brand: Marca del auto mencionado (si está en el contexto)
- model: Modelo del auto mencionado (si está en el contexto)
- budget_max: Precio del auto mencionado en MXN (si está en el contexto, como número entero). Este campo debe contener el precio EXACTO del auto que se mencionó anteriormente.
- year_min o year_max: Año del auto (si está en el contexto, usa el mismo valor para ambos si solo hay un año)

Si no encuentras alguna información, déjala como None.
Solo extrae información que esté EXPLÍCITAMENTE mencionada en el contexto previo."""

            try:
                car_info = await self.llm_manager.complete_structured_text(
                    prompt=extraction_prompt,
                    response_schema=CarPreferences,
                    temperature=0.1,
                    max_tokens=200,
                )

                info_dict = car_info.model_dump(exclude_none=True)

                if "budget_max" in info_dict:
                    price = info_dict["budget_max"]
                    if price:
                        if 100000 <= price <= 10000000:
                            return info_dict
                        else:
                            info_dict.pop("budget_max", None)

                if info_dict:
                    return info_dict

                return None

            except Exception as exc:
                logger.warning(f"Error in structured extraction from context: {exc}")
                return None

        except Exception as exc:
            logger.warning(f"Error extracting car info from context: {exc}")
            return None
