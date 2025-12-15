from typing import Dict, Any, List, Optional, Set
from app.core.config.logging import logger
from app.repository.vector import QdrantVectorRepository
from app.repository.vector import CollectionType
from app.core.services.kavak_llm_manager import KavakLLMManager
from app.models.agent.schemas import CarPreferences, FinancingPlan, Car, RAGAnswer
from app.utils.normalize import find_closest_make, find_closest_model

_known_makes_cache: Optional[Set[str]] = None
_known_models_cache: Optional[Set[str]] = None


async def load_known_makes_models(
    vector_repository: QdrantVectorRepository,
) -> tuple[Set[str], Set[str]]:
    """Load known makes and models from the catalog for fuzzy matching."""
    global _known_makes_cache, _known_models_cache

    if _known_makes_cache is not None and _known_models_cache is not None:
        return _known_makes_cache, _known_models_cache

    try:
        dummy_embedding = [0.0] * 1536

        results = await vector_repository.search(
            vector=dummy_embedding,
            top_k=1000,
            collection=CollectionType.KAVAK_CATALOG,
        )

        makes = set()
        models = set()

        for result in results:
            payload = result.payload if hasattr(result, "payload") else {}
            if make := payload.get("make"):
                makes.add(str(make).strip())
            if model := payload.get("model"):
                models.add(str(model).strip())

        _known_makes_cache = makes
        _known_models_cache = models

        logger.info(
            f"Loaded {len(makes)} makes and {len(models)} models for fuzzy matching"
        )
        return makes, models

    except Exception as exc:
        logger.warning(f"Error loading known makes/models: {exc}, using empty sets")
        _known_makes_cache = set()
        _known_models_cache = set()
        return _known_makes_cache, _known_models_cache


async def rag_value_prop_tool(
    query: str,
    vector_repository: QdrantVectorRepository,
    llm_manager: KavakLLMManager,
    top_k: int = 5,
) -> RAGAnswer:
    logger.info("Generating RAG answer")

    try:
        embedding = await llm_manager.embed_text(query)

        results = await vector_repository.search(
            vector=embedding,
            top_k=top_k,
            collection=CollectionType.KAVAK_VALUE_PROP,
        )

        if not results or len(results) == 0:
            return RAGAnswer(
                answer="Lo siento, no encontré información relevante sobre ese tema. ¿Podrías reformular tu pregunta?",
                sources=[],
            )

        context_parts = []
        sources = []

        for result in results:
            payload = result.payload if hasattr(result, "payload") else {}
            text = payload.get("text", "")
            category = payload.get("category", "general")
            topic = payload.get("topic", "")
            location = payload.get("location_name", "")

            if text:
                context_parts.append(text)
                source_parts = []
                if location:
                    source_parts.append(location)
                if category:
                    source_parts.append(category)
                if topic:
                    source_parts.append(topic)
                sources.append(" | ".join(source_parts) if source_parts else "Kavak")

        context = "\n\n".join(context_parts)

        prompt = f"""Eres un asistente comercial de Kavak. Responde la pregunta del usuario usando SOLO la información proporcionada en el contexto.

Contexto sobre Kavak:
{context}

Pregunta del usuario: {query}

Instrucciones:
- Responde de manera clara, concisa y amigable
- Usa SOLO la información del contexto proporcionado
- Si la información no está en el contexto, di que no tienes esa información específica
- Responde en español mexicano
- Sé profesional pero cercano, como un agente comercial real

Respuesta:"""

        answer = await llm_manager.complete_text(
            prompt=prompt,
            temperature=0.3,
            max_tokens=500,
        )

        answer = answer.strip()
        if answer.startswith("Respuesta:"):
            answer = answer.replace("Respuesta:", "").strip()

        return RAGAnswer(answer=answer, sources=sources)

    except Exception as exc:
        logger.error(f"Error in rag_value_prop_tool: {exc}", exc_info=True)
        return RAGAnswer(
            answer="Lo siento, no pude encontrar información sobre eso. ¿Puedes reformular tu pregunta?",
            sources=[],
        )


async def search_catalog_tool(
    preferences: CarPreferences,
    vector_repository: QdrantVectorRepository,
    llm_manager: KavakLLMManager,
    top_k: int = 20,
) -> List[Car]:
    logger.info(f"Searching catalog with preferences: {preferences}")

    try:
        normalized_prefs = preferences.model_dump(exclude_none=True)
        make = normalized_prefs.get("brand")
        model = normalized_prefs.get("model")

        if make:
            try:
                known_makes, known_models = await load_known_makes_models(
                    vector_repository
                )
                normalized_make = find_closest_make(make, known_makes, threshold=70)
                if normalized_make:
                    if normalized_make.lower() != make.lower():
                        logger.info(f"Normalized make '{make}' to '{normalized_make}'")
                    normalized_prefs["brand"] = normalized_make
                    preferences.brand = normalized_make
            except Exception as exc:
                logger.warning(f"Error normalizing make: {exc}, using original")

        if model:
            try:
                known_makes, known_models = await load_known_makes_models(
                    vector_repository
                )
                normalized_model = find_closest_model(model, known_models, threshold=70)
                if normalized_model:
                    if normalized_model.lower() != model.lower():
                        logger.info(
                            f"Normalized model '{model}' to '{normalized_model}'"
                        )
                    normalized_prefs["model"] = normalized_model
                    preferences.model = normalized_model
            except Exception as exc:
                logger.warning(f"Error normalizing model: {exc}, using original")

        query_text = _build_catalog_query(preferences)
        embedding = await llm_manager.embed_text(query_text)
        filters = _build_qdrant_filters(preferences)

        results = await vector_repository.search(
            vector=embedding,
            top_k=top_k * 2,
            filter_by=filters if filters else None,
            collection=CollectionType.KAVAK_CATALOG,
        )

        if not results and filters.get("make"):
            logger.info(
                f"No results with exact brand filter '{filters.get('make')}', trying fallback strategies..."
            )

            brand_to_match = filters.get("make").lower().strip()
            results_unfiltered = await vector_repository.search(
                vector=embedding,
                top_k=top_k * 4,
                filter_by=None,
                collection=CollectionType.KAVAK_CATALOG,
            )

            filtered_results = []
            for result in results_unfiltered:
                payload = result.payload if hasattr(result, "payload") else {}
                make_in_result = str(payload.get("make", "")).lower().strip()
                if make_in_result == brand_to_match:
                    filtered_results.append(result)

            if filtered_results:
                logger.info(
                    f"Found {len(filtered_results)} results with case-insensitive brand match"
                )
                results = filtered_results
            else:
                logger.info("Trying semantic search without brand filter...")
                filters_without_brand = {
                    k: v for k, v in filters.items() if k != "make"
                }
                results = await vector_repository.search(
                    vector=embedding,
                    top_k=top_k * 2,
                    filter_by=filters_without_brand if filters_without_brand else None,
                    collection=CollectionType.KAVAK_CATALOG,
                )

                if results:
                    brand_filtered = [
                        r
                        for r in results
                        if str(
                            r.payload.get("make", "") if hasattr(r, "payload") else {}
                        )
                        .lower()
                        .strip()
                        == brand_to_match
                    ]
                    if brand_filtered:
                        logger.info(
                            f"Found {len(brand_filtered)} results with semantic search + brand filter"
                        )
                        results = brand_filtered

        if not results or len(results) == 0:
            logger.info(
                "No cars found matching preferences after all fallback strategies"
            )
            return []

        cars = _rerank_and_convert(results, preferences)
        return cars[:top_k]

    except Exception as exc:
        logger.error(f"Error in search_catalog_tool: {exc}", exc_info=True)
        return []


async def compute_financing_tool(
    price: float,
    down_payment: float,
    years: int = 3,
    interest_rate: float = 0.10,
) -> FinancingPlan:
    logger.info(
        f"Computing financing: price={price}, down={down_payment}, rate={interest_rate}, years={years}"
    )

    try:
        if price <= 0:
            raise ValueError("Price must be positive")
        if down_payment < 0:
            raise ValueError("Down payment cannot be negative")
        if down_payment >= price:
            raise ValueError("Down payment must be less than price")
        if years < 3 or years > 6:
            raise ValueError("Financing term must be between 3 and 6 years")
        if interest_rate < 0 or interest_rate > 1:
            raise ValueError("Interest rate must be between 0 and 1")

        principal = price - down_payment
        monthly_rate = interest_rate / 12
        months = years * 12

        if monthly_rate == 0:
            monthly_payment = principal / months
        else:
            monthly_payment = (
                principal
                * monthly_rate
                * (1 + monthly_rate) ** months
                / ((1 + monthly_rate) ** months - 1)
            )

        total_amount = monthly_payment * months
        total_interest = total_amount - principal

        return FinancingPlan(
            monthly_payment=round(monthly_payment, 2),
            total_interest=round(total_interest, 2),
            total_amount=round(total_amount, 2),
            principal=round(principal, 2),
            interest_rate=interest_rate,
            term_years=years,
            term_months=months,
        )

    except Exception as exc:
        logger.error(f"Error computing financing: {exc}")
        raise


def _build_catalog_query(preferences: CarPreferences) -> str:
    parts = []

    if preferences.brand:
        parts.append(f"marca {preferences.brand}")
    if preferences.model:
        parts.append(f"modelo {preferences.model}")

    if preferences.year_min and preferences.year_max:
        parts.append(f"año {preferences.year_min} a {preferences.year_max}")
    elif preferences.year_min:
        parts.append(f"año desde {preferences.year_min}")
    elif preferences.year_max:
        parts.append(f"año hasta {preferences.year_max}")

    if preferences.budget_max:
        parts.append(f"precio hasta {preferences.budget_max} pesos")

    if preferences.transmission:
        if preferences.transmission == "automatic":
            parts.append("transmisión automática")
        elif preferences.transmission == "manual":
            parts.append("transmisión manual")

    if preferences.fuel:
        fuel_map = {
            "gasoline": "gasolina",
            "diesel": "diésel",
            "hybrid": "híbrido",
            "electric": "eléctrico",
        }
        parts.append(f"combustible {fuel_map.get(preferences.fuel, preferences.fuel)}")

    if preferences.mileage_max:
        parts.append(f"kilometraje bajo hasta {preferences.mileage_max} km")

    if parts:
        query = "auto " + " ".join(parts)
    else:
        query = "auto seminuevo"

    return query


def _build_qdrant_filters(preferences: CarPreferences) -> Dict[str, Any]:
    """Build Qdrant filters from preferences for hard constraints."""
    filters = {}

    if preferences.budget_max:
        filters["price"] = {"lte": float(preferences.budget_max)}

    year_filters = {}
    if preferences.year_min:
        year_filters["gte"] = int(preferences.year_min)
    if preferences.year_max:
        year_filters["lte"] = int(preferences.year_max)
    if year_filters:
        filters["year"] = year_filters

    if preferences.mileage_max:
        filters["km"] = {"lte": int(preferences.mileage_max)}

    if preferences.brand:
        filters["make"] = preferences.brand.strip()

    if preferences.model:
        filters["model"] = preferences.model.strip()

    return filters


def _rerank_and_convert(results: List[Any], preferences: CarPreferences) -> List[Car]:
    cars_with_scores = []

    for result in results:
        payload = result.payload if hasattr(result, "payload") else {}
        score = result.score if hasattr(result, "score") else 0.0

        try:
            stock_id = str(payload.get("stock_id", ""))
            make = payload.get("make", "").strip()
            model = payload.get("model", "").strip()
            year = int(payload.get("year", 0)) if payload.get("year") else None
            price = float(payload.get("price", 0)) if payload.get("price") else None
            km = int(payload.get("km", 0)) if payload.get("km") else None

            if not stock_id or not make or not model or not year or not price:
                continue

            rerank_score = score

            if preferences.brand and make.lower() == preferences.brand.lower():
                rerank_score += 0.2

            if preferences.model and model.lower() == preferences.model.lower():
                rerank_score += 0.2

            if preferences.budget_max and price:
                budget_ratio = price / float(preferences.budget_max)
                if budget_ratio <= 1.0:
                    if 0.7 <= budget_ratio <= 0.95:
                        rerank_score += 0.15
                    elif budget_ratio > 0.95:
                        rerank_score += 0.1
                    else:
                        rerank_score += 0.05

            if year:
                year_score = (year - 2000) / 24.0
                rerank_score += year_score * 0.1

            if km:
                mileage_score = 1.0 - min(km / 200000.0, 1.0)
                rerank_score += mileage_score * 0.1

            bluetooth = payload.get("bluetooth", False)
            car_play = payload.get("car_play", False)
            version = payload.get("version", "")
            largo = float(payload.get("largo", 0)) if payload.get("largo") else None
            ancho = float(payload.get("ancho", 0)) if payload.get("ancho") else None
            altura = float(payload.get("altura", 0)) if payload.get("altura") else None

            car = Car(
                id=stock_id,
                brand=make,
                model=model,
                year=year,
                price=price,
                mileage=km or 0,
                version=version if version else None,
                bluetooth=bluetooth if bluetooth else None,
                car_play=car_play if car_play else None,
                length=largo if largo else None,
                width=ancho if ancho else None,
                height=altura if altura else None,
                transmission=payload.get("transmission"),
                fuel=payload.get("fuel"),
                city=payload.get("city"),
                url=f"https://kavak.com/mx/auto/{stock_id}" if stock_id else None,
            )

            cars_with_scores.append((rerank_score, car))

        except (ValueError, TypeError, KeyError) as exc:
            logger.warning(f"Error processing car result: {exc}, payload: {payload}")
            continue

    cars_with_scores.sort(key=lambda x: x[0], reverse=True)
    return [car for _, car in cars_with_scores]
