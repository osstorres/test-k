from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from qdrant_client.models import Distance


class CollectionType(str, Enum):
    KAVAK_CATALOG = "kavak_catalog"
    KAVAK_VALUE_PROP = "kavak_value_prop"


@dataclass(frozen=True)
class CollectionConfig:
    name: str
    vector_size: int
    distance: Distance = Distance.COSINE
    description: str = ""
    embedding_model: str | None = None
    namespace_enabled: bool = True

    @staticmethod
    def get_distance(name: str) -> Distance:
        lower = (name or "").lower()
        if lower == "cosine":
            return Distance.COSINE
        if lower == "euclid":
            return Distance.EUCLID
        if lower == "dot":
            return Distance.DOT
        return Distance.COSINE


COLLECTION_REGISTRY: dict[CollectionType, CollectionConfig] = {
    CollectionType.KAVAK_CATALOG: CollectionConfig(
        name="kavak_catalog",
        vector_size=1536,
        distance=Distance.COSINE,
        description="Catálogo de autos seminuevos de Kavak",
        embedding_model="openai-text-embedding-3-small",
        namespace_enabled=False,
    ),
    CollectionType.KAVAK_VALUE_PROP: CollectionConfig(
        name="kavak_value_prop",
        vector_size=1536,
        distance=Distance.COSINE,
        description="Propuesta de valor, beneficios y sedes de Kavak",
        embedding_model="openai-text-embedding-3-small",
        namespace_enabled=False,
    ),
}


def get_collection_config(collection_type: CollectionType) -> CollectionConfig:
    return COLLECTION_REGISTRY[collection_type]


def create_custom_collection_config(
    name: str,
    vector_size: int,
    distance: Literal["cosine", "euclid", "dot"] = "cosine",
    description: str = "",
    embedding_model: str | None = None,
    namespace_enabled: bool = True,
) -> CollectionConfig:
    return CollectionConfig(
        name=name,
        vector_size=vector_size,
        distance=CollectionConfig.get_distance(distance),
        description=description,
        embedding_model=embedding_model,
        namespace_enabled=namespace_enabled,
    )
