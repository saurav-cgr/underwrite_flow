"""Administrator-only synthetic evaluation endpoint."""

from fastapi import APIRouter, Depends

from underwriteflow.auth.dependencies import require_role
from underwriteflow.auth.schemas import UserRole
from underwriteflow.evaluation.runner import run_evaluation

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


# Return safe aggregate metrics without exposing synthetic case payloads.
@router.get("/summary")
async def evaluation_summary(
    _: dict[str, str] = Depends(require_role(UserRole.ADMINISTRATOR.value)),
) -> dict:
    return await run_evaluation()
