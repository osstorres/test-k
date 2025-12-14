"""
Vector database persistence layer

Provides interfaces for Qdrant vector database operations with collection support.
"""

from app.persistence.vector.qdrant_repository import QdrantVectorRepository
from app.persistence.vector.collection_config import (
    CollectionType,
    CollectionConfig,
    get_collection_config,
    create_custom_collection_config,
    COLLECTION_REGISTRY,
)

__all__ = [
    "QdrantVectorRepository",
    "CollectionType",
    "CollectionConfig",
    "get_collection_config",
    "create_custom_collection_config",
    "COLLECTION_REGISTRY",
]
