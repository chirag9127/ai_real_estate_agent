from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from app.database import get_db
from app.schemas.ranking import RankingResponse, RankingsListResponse
from app.services.ranking_service import get_rankings_by_pipeline_run

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

router = APIRouter(prefix="/rankings")


@router.get("/{pipeline_run_id}", response_model=RankingsListResponse)
def get_rankings(
    pipeline_run_id: int,
    db: Session = Depends(get_db),
) -> RankingsListResponse:
    """Get ranked results for a pipeline run."""
    ranked_results = get_rankings_by_pipeline_run(db, pipeline_run_id)
    rankings = [RankingResponse.model_validate(rr) for rr in ranked_results]
    return RankingsListResponse(
        pipeline_run_id=pipeline_run_id,
        rankings=rankings,
        total=len(rankings),
    )
