from typing import Dict, Any, List, Optional, Set
import asyncio
from app.core.config.logging import logger
from app.persistence.vector.qdrant_repository import QdrantVectorRepository
from app.persistence.vector.collection_config import CollectionType
from app.core.services.kavak_llm_manager import KavakLLMManager
from app.domain.agent_kavak.workflows.schemas import CarPreferences, Car
from app.utils.normalize import find_closest_make, find_closest_model

_known_makes_cache: Optional[Set[str]] = None
_known_models_cache: Optional[Set[str]] = None


async def load_known_makes_models(
    vector_repository: QdrantVectorRepository,
) -> tuple[Set[str], Set[str]]:
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


async def retrieve_context(
    query: str,
    preferences: Optional[CarPreferences] = None,
    vector_repository: Optional[QdrantVectorRepository] = None,
    llm_manager: Optional[KavakLLMManager] = None,
    catalog_top_k: int = 5,
    value_prop_top_k: int = 3,
) -> Dict[str, Any]:
    logger.info("Retrieving context.")

    catalog_results = []

    if preferences:
        catalog_results, value_prop_results = await asyncio.gather(
            _retrieve_catalog_optimized(
                preferences=preferences,
                query_text=query,
                vector_repository=vector_repository,
                llm_manager=llm_manager,
                top_k=catalog_top_k,
            ),
            _retrieve_value_prop_optimized(
                query=query,
                vector_repository=vector_repository,
                llm_manager=llm_manager,
                top_k=value_prop_top_k,
            ),
        )
    else:
        value_prop_results = await _retrieve_value_prop_optimized(
            query=query,
            vector_repository=vector_repository,
            llm_manager=llm_manager,
            top_k=value_prop_top_k,
        )

    return {
        "catalog_results": catalog_results,
        "value_prop_results": value_prop_results,
    }


async def _retrieve_catalog_optimized(
    preferences: CarPreferences,
    query_text: str,
    vector_repository: QdrantVectorRepository,
    llm_manager: KavakLLMManager,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    try:
        normalized_prefs = preferences.model_dump(exclude_none=True)
        make = normalized_prefs.get("brand")
        model = normalized_prefs.get("model")

        known_makes, known_models = await load_known_makes_models(vector_repository)

        if make:
            normalized_make = find_closest_make(make, known_makes, threshold=70)
            if normalized_make:
                normalized_prefs["brand"] = normalized_make

        if model:
            normalized_model = find_closest_model(model, known_models, threshold=70)
            if normalized_model:
                normalized_prefs["model"] = normalized_model

        filters = _build_qdrant_filters_optimized(normalized_prefs)

        query_embedding = await llm_manager.embed_text(query_text or "auto seminuevo")

        results = await vector_repository.search(
            vector=query_embedding,
            top_k=top_k * 2,
            filter_by=filters if filters else None,
            collection=CollectionType.KAVAK_CATALOG,
        )

        if not results and filters.get("make"):
            logger.info(
                f"No results with exact brand filter '{filters.get('make')}', trying case-insensitive search..."
            )
            results_unfiltered = await vector_repository.search(
                vector=query_embedding,
                top_k=top_k * 4,
                filter_by=None,
                collection=CollectionType.KAVAK_CATALOG,
            )

            brand_to_match = filters.get("make").lower().strip()
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
                filters_without_brand = {
                    k: v for k, v in filters.items() if k != "make"
                }
                results = await vector_repository.search(
                    vector=query_embedding,
                    top_k=top_k * 2,
                    filter_by=filters_without_brand if filters_without_brand else None,
                    collection=CollectionType.KAVAK_CATALOG,
                )

        if not results:
            return []

        cars = _convert_results_to_cars(results)

        return [car.model_dump() for car in cars[:top_k]]

    except Exception as exc:
        logger.error(f"Error in optimized catalog retrieval: {exc}", exc_info=True)
        return []


async def _retrieve_value_prop_optimized(
    query: str,
    vector_repository: QdrantVectorRepository,
    llm_manager: KavakLLMManager,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """
    Optimized value prop retrieval with smaller chunks (already done in loader).

    Returns top_k chunks (optimized: 2-5, default 3).
    """
    try:
        embedding = await llm_manager.embed_text(query)

        results = await vector_repository.search(
            vector=embedding,
            top_k=top_k,
            collection=CollectionType.KAVAK_VALUE_PROP,
        )

        if not results:
            return []

        value_prop_results = []
        for result in results:
            payload = result.payload if hasattr(result, "payload") else {}
            value_prop_results.append(
                {
                    "text": payload.get("text", ""),
                    "category": payload.get("category", "general"),
                    "state": payload.get("state", "general"),
                    "location_name": payload.get("location_name"),
                    "topic": payload.get("topic", ""),
                }
            )

        return value_prop_results

    except Exception as exc:
        logger.error(f"Error in optimized value prop retrieval: {exc}", exc_info=True)
        return []


def _build_qdrant_filters_optimized(preferences_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Build Qdrant filters from preferences (hard constraints first)."""
    filters = {}

    if budget_max := preferences_dict.get("budget_max"):
        filters["price"] = {"lte": float(budget_max)}

    year_filters = {}
    if year_min := preferences_dict.get("year_min"):
        year_filters["gte"] = int(year_min)
    if year_max := preferences_dict.get("year_max"):
        year_filters["lte"] = int(year_max)
    if year_filters:
        filters["year"] = year_filters

    if mileage_max := preferences_dict.get("mileage_max"):
        filters["km"] = {"lte": int(mileage_max)}

    if brand := preferences_dict.get("brand"):
        brand_str = str(brand).strip()
        filters["make"] = brand_str

    if model := preferences_dict.get("model"):
        filters["model"] = str(model).strip()

    return filters


def _convert_results_to_cars(results: List[Any]) -> List[Car]:
    """Convert Qdrant results to Car objects."""
    cars = []

    for result in results:
        payload = result.payload if hasattr(result, "payload") else {}

        try:
            stock_id = str(payload.get("stock_id", ""))
            make = payload.get("make", "").strip()
            model = payload.get("model", "").strip()
            year = int(payload.get("year", 0)) if payload.get("year") else None
            price = float(payload.get("price", 0)) if payload.get("price") else None
            km = int(payload.get("km", 0)) if payload.get("km") else None

            if not stock_id or not make or not model or not year or not price:
                continue

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
                city=payload.get("city", ""),
                url=f"https://kavak.com/mx/auto/{stock_id}" if stock_id else None,
            )
            cars.append(car)

        except (ValueError, TypeError, KeyError) as exc:
            logger.warning(f"Error converting car result: {exc}")
            continue

            return cars
