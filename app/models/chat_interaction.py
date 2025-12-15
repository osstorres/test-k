from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any


class ChatInteraction(BaseModel):
    id: Optional[int] = Field(None, description="ID de la interacción")
    user_id: str = Field(..., description="Identificador único del usuario")
    session_id: Optional[str] = Field(None, description="ID de sesión de chat")
    query: str = Field(..., description="Consulta o mensaje del usuario")
    response: str = Field(..., description="Respuesta del asistente")
    intent: Optional[str] = Field(
        None, description="Intención detectada (valueprop, catalog, financing, other)"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata adicional")
    created_at: Optional[datetime] = Field(None, description="Timestamp de creación")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ChatInteractionCreate(BaseModel):
    user_id: str = Field(..., description="Identificador único del usuario")
    session_id: Optional[str] = Field(None, description="ID de sesión de chat")
    query: str = Field(..., description="Consulta o mensaje del usuario")
    response: str = Field(..., description="Respuesta del asistente")
    intent: Optional[str] = Field(None, description="Intención detectada")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata adicional")


class ChatContext(BaseModel):
    user_id: str = Field(..., description="Identificador único del usuario")
    interactions: list[ChatInteraction] = Field(
        default_factory=list, description="Lista de interacciones"
    )

    def to_context_string(self) -> str:
        if not self.interactions:
            return ""

        context_parts = ["## Contexto de Conversaciones Previas\n"]
        for i, interaction in enumerate(self.interactions, 1):
            context_parts.append(f"{i}. Usuario: {interaction.query}")
            context_parts.append(f"   Asistente: {interaction.response}")

        return "\n".join(context_parts)
