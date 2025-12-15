from typing import Optional, Dict, Any
from llama_index.core.workflow import Event
from pydantic import Field


class RoutingEvent(Event):
    intent: str = Field(description="Intent: valueprop, catalog, financing, or other")
    confidence: float = Field(description="Confidence score")
    preferences: Optional[Dict[str, Any]] = Field(
        None, description="Extracted preferences/filters"
    )
    query: str = Field(description="Original query")
    complexity: str = Field(
        default="simple", description="Complexity level: simple or complex"
    )
