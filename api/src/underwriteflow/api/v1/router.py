"""Version 1 API router."""

from fastapi import APIRouter

router = APIRouter()


# Expose the stable versioned API namespace.
@router.get("", tags=["system"])
async def api_root() -> dict[str, str]:
    return {"status": "available"}
