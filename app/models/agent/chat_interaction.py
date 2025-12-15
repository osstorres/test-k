from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any


class ChatInteraction(BaseModel):
    id: Optional[int] = Field(None, description="Interaction ID")
    user_id: str = Field(..., description="Unique user identifier")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    query: str = Field(..., description="User query or message")
    response: str = Field(..., description="Assistant response")
    intent: Optional[str] = Field(
        None, description="Detected intent (valueprop, catalog, financing, other)"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ChatInteractionCreate(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    session_id: Optional[str] = Field(None, description="Chat session ID")
    query: str = Field(..., description="User query or message")
    response: str = Field(..., description="Assistant response")
    intent: Optional[str] = Field(None, description="Detected intent")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ChatContext(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    interactions: list[ChatInteraction] = Field(
        default_factory=list, description="List of interactions"
    )

    def to_context_string(self) -> str:
        if not self.interactions:
            return ""

        context_parts = ["## Previous Conversation Context\n"]
        for i, interaction in enumerate(self.interactions, 1):
            context_parts.append(f"{i}. User: {interaction.query}")
            context_parts.append(f"   Assistant: {interaction.response}")

        return "\n".join(context_parts)
