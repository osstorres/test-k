from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Sequence
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
)
from app.core.manager import settings
from app.repository.vector.collection_config import (
    CollectionType,
    get_collection_config,
)


class QdrantVectorRepository:
    _instance: "QdrantVectorRepository | None" = None

    def __init__(self):
        self._client = AsyncQdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            grpc_port=settings.QDRANT_GRPC_PORT,
            api_key=settings.QDRANT_API_KEY,
            https=True,
            timeout=settings.QDRANT_POOL_TIMEOUT,
            check_compatibility=False,
        )
        self._semaphore = asyncio.Semaphore(settings.QDRANT_POOL_MAX_SIZE)

    @classmethod
    def get_instance(cls) -> "QdrantVectorRepository":
        if cls._instance is None:
            cls._instance = QdrantVectorRepository()
        return cls._instance

    @retry(
        reraise=True,
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def upsert_vectors(
        self,
        points: Sequence[PointStruct],
        collection: Optional[CollectionType | str] = None,
    ) -> None:
        collection_name = self._resolve_collection_name(collection)
        async with self._semaphore:
            await self._client.upsert(collection_name=collection_name, points=points)

    @retry(
        reraise=True,
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def search(
        self,
        vector: List[float],
        top_k: int = 5,
        filter_by: Optional[Dict[str, Any]] = None,
        collection: Optional[CollectionType | str] = None,
    ):
        collection_name = self._resolve_collection_name(collection)

        async with self._semaphore:
            qdrant_filter = None
            if filter_by:
                conditions = []
                for k, v in filter_by.items():
                    if isinstance(v, dict) and any(
                        key in v for key in ["gte", "lte", "gt", "lt"]
                    ):
                        from qdrant_client.models import Range

                        conditions.append(FieldCondition(key=k, range=Range(**v)))
                    elif isinstance(v, list):
                        conditions.append(FieldCondition(key=k, match=MatchAny(any=v)))
                    else:
                        conditions.append(
                            FieldCondition(key=k, match=MatchValue(value=v))
                        )
                qdrant_filter = Filter(must=conditions)
            response = await self._client.query_points(
                collection_name=collection_name,
                query=vector,
                limit=top_k,
                query_filter=qdrant_filter,
            )
            return response.points

    @retry(
        reraise=True,
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def delete_by_ids(
        self,
        ids: List[str],
        collection: Optional[CollectionType | str] = None,
    ) -> None:
        collection_name = self._resolve_collection_name(collection)
        async with self._semaphore:
            await self._client.delete(
                collection_name=collection_name, points_selector=ids
            )

    def _resolve_collection_name(
        self, collection: Optional[CollectionType | str] = None
    ) -> str:
        if collection is None:
            raise ValueError("Collection name must be provided")

        if isinstance(collection, CollectionType):
            config = get_collection_config(collection)
            return config.name

        return collection

    async def aclose(self) -> None:
        await self._client.close()
