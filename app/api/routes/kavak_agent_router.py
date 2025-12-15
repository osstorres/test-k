from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config.logging import logger
from app.core.dependencies import KavakLLMDep, QdrantRepoDep, MemoryManagerDep
from app.domain.agent_kavak.facade import KavakAgentFacade


router = APIRouter(prefix="/kavak", tags=["kavak-agent"])


class KavakQueryRequest(BaseModel):
    query: str = Field(..., description="User query/message")
    user_id: Optional[str] = Field(None, description="User ID for memory context")


class KavakQueryResponse(BaseModel):
    response: str = Field(..., description="Agent response message")
    user_id: Optional[str] = Field(None, description="User ID")
    agent: str = Field(..., description="Agent name")
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="LLM model used")


async def get_kavak_facade(
    llm_manager: KavakLLMDep,
    vector_repository: QdrantRepoDep,
    memory_manager: MemoryManagerDep,
) -> KavakAgentFacade:
    return KavakAgentFacade(
        llm_manager=llm_manager,
        vector_repository=vector_repository,
        memory_manager=memory_manager,
    )


@router.post(
    "/chat",
    summary="Process a chat message",
    description="Process a chat message using the Kavak commercial sales agent. Returns non-streaming response for WhatsApp.",
    response_model=KavakQueryResponse,
)
async def process_kavak_chat(
    request: KavakQueryRequest,
    facade: KavakAgentFacade = Depends(get_kavak_facade),
) -> KavakQueryResponse:
    try:
        logger.info(f"Processing Kavak chat query for user: {request.user_id}")

        result = await facade.process_query(
            query=request.query,
            user_id=request.user_id,
        )

        return KavakQueryResponse(
            response=result.get("response", ""),
            user_id=result.get("user_id"),
            agent=result.get("agent", "kavak_agent"),
            provider=result.get("provider", "openai"),
            model=result.get("model", "gpt-4o-mini"),
        )

    except Exception as exc:
        logger.error(f"Error processing Kavak chat query: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(exc)}",
        )
