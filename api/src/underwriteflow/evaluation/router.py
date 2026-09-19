"""Administrator-only synthetic evaluation endpoints."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from underwriteflow.auth.dependencies import require_permission
from underwriteflow.auth.schemas import Permission
from underwriteflow.evaluation.runner import run_evaluation

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class EvaluationRunRequest(BaseModel):
    """Optional split selector for one evaluation run."""

    split: Literal["development", "holdout"] | None = None


# Run the reference set on demand and return safe aggregate metrics. The run is
# an explicit action because it executes all 90 cases through the pipeline.
@router.post("/run")
async def run_synthetic_evaluation(
    command: EvaluationRunRequest | None = None,
    _: dict[str, str] = Depends(
        require_permission(Permission.EVALUATION_RUN)
    ),
) -> dict:
    return await run_evaluation(command.split if command else None)
