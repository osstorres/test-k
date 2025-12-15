from __future__ import annotations
from typing import Optional
import json
import hashlib
import redis.asyncio as aioredis
from app.core.config.logging import logger
from app.core.config.settings.redis_config import RedisSettings
from app.models.agent.schemas import RAGAnswer


class CAGManager:
    _instance: Optional[CAGManager] = None
    _initialized: bool = False
    _redis_client: Optional[aioredis.Redis] = None

    def __new__(cls) -> CAGManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.settings = RedisSettings()
        self._initialized = True

    async def _get_redis_client(self) -> aioredis.Redis:
        if self._redis_client is None:
            connection_kwargs = {
                "host": self.settings.HOST,
                "port": self.settings.PORT,
                "decode_responses": self.settings.DECODE_RESPONSES,
            }

            if self.settings.USERNAME:
                connection_kwargs["username"] = self.settings.USERNAME
            if self.settings.PASSWORD:
                connection_kwargs["password"] = self.settings.PASSWORD

            try:
                self._redis_client = aioredis.Redis(**connection_kwargs)
                await self._redis_client.ping()
                logger.info(
                    f"Connected to Redis at {self.settings.HOST}:{self.settings.PORT}"
                )
            except Exception as exc:
                logger.warning(f"Failed to connect to Redis: {exc}")
                raise

        return self._redis_client

    def _query_to_hash(self, query: str) -> str:
        query_normalized = query.lower().strip()
        return hashlib.md5(query_normalized.encode()).hexdigest()

    def _build_cache_key(self, cache_type: str, query: str) -> str:
        query_hash = self._query_to_hash(query)
        return f"{self.settings.CAG_KEY_PREFIX}:{cache_type}:{query_hash}"

    async def get_cached_response(
        self, cache_type: str, query: str
    ) -> Optional[RAGAnswer]:
        try:
            redis_client = await self._get_redis_client()
            cache_key = self._build_cache_key(cache_type, query)

            cached_data = await redis_client.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)
                return RAGAnswer(**data)

            return None

        except Exception as exc:
            logger.debug(
                f"Error getting cached response (falling back to RAG): {exc}",
                exc_info=False,
            )
            return None

    async def cache_response(
        self,
        cache_type: str,
        query: str,
        response: RAGAnswer,
        ttl: Optional[int] = None,
    ) -> bool:
        try:
            redis_client = await self._get_redis_client()
            cache_key = self._build_cache_key(cache_type, query)

            ttl = ttl or self.settings.CAG_TTL

            data = {
                "answer": response.answer,
                "sources": response.sources,
            }

            await redis_client.setex(cache_key, ttl, json.dumps(data))

            return True

        except Exception as exc:
            logger.warning(f"Error caching response (non-fatal): {exc}", exc_info=False)
            return False

    async def invalidate_cache(
        self, cache_type: Optional[str] = None, pattern: Optional[str] = None
    ) -> int:
        try:
            redis_client = await self._get_redis_client()

            if pattern:
                search_pattern = pattern
            elif cache_type:
                search_pattern = f"{self.settings.CAG_KEY_PREFIX}:{cache_type}:*"
            else:
                search_pattern = f"{self.settings.CAG_KEY_PREFIX}:*"

            keys = []
            async for key in redis_client.scan_iter(match=search_pattern):
                keys.append(key)

            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info(
                    f"Invalidated {deleted} cache entries matching: {search_pattern}"
                )
                return deleted

            return 0

        except Exception as exc:
            logger.error(f"Error invalidating cache: {exc}", exc_info=True)
            return 0


_cag_manager_instance: Optional[CAGManager] = None


def get_cag_manager() -> CAGManager:
    global _cag_manager_instance
    if _cag_manager_instance is None:
        _cag_manager_instance = CAGManager()
    return _cag_manager_instance
