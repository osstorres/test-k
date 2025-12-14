import fastapi
from fastapi import status

router = fastapi.APIRouter(prefix="", tags=["utils"])


@router.get(path="/health", name="utils:health-check", status_code=status.HTTP_200_OK)
async def health_check() -> bool:
    return True
