from fastapi import APIRouter, HTTPException

from app.core.config.logging import logger
from app.core.dependencies import KavakFacadeDep
from app.models.api.api_schemas import KavakQueryRequest, KavakQueryResponse


router = APIRouter(prefix="/kavak", tags=["kavak-agent"])


@router.post(
    "/chat",
    summary="Process a chat message",
    description="Process a chat message using the Kavak commercial sales agent. Returns non-streaming response for WhatsApp.",
    response_model=KavakQueryResponse,
)
async def process_kavak_chat(
    request: KavakQueryRequest,
    facade: KavakFacadeDep,
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
