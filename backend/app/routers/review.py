from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.schemas.ranking import RankingResponse, RankingsListResponse
from app.services import review_service

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

router = APIRouter(prefix="/review")


class ApproveRequest(BaseModel):
    ranking_ids: list[int]


@router.get("/{pipeline_run_id}", response_model=RankingsListResponse)
def get_pending_review(
    pipeline_run_id: int,
    db: Session = Depends(get_db),
) -> RankingsListResponse:
    rankings = review_service.get_pending_review(db, pipeline_run_id)
    return RankingsListResponse(
        pipeline_run_id=pipeline_run_id,
        rankings=[RankingResponse.model_validate(rr) for rr in rankings],
        total=len(rankings),
    )


@router.post("/{pipeline_run_id}/approve", response_model=RankingsListResponse)
def approve_listings(
    pipeline_run_id: int,
    body: ApproveRequest,
    db: Session = Depends(get_db),
) -> RankingsListResponse:
    rankings = review_service.approve_listings(db, pipeline_run_id, body.ranking_ids)
    return RankingsListResponse(
        pipeline_run_id=pipeline_run_id,
        rankings=[RankingResponse.model_validate(rr) for rr in rankings],
        total=len(rankings),
    )


@router.post("/{pipeline_run_id}/reject/{ranking_id}", response_model=RankingResponse)
def reject_listing(
    pipeline_run_id: int,
    ranking_id: int,
    db: Session = Depends(get_db),
) -> RankingResponse:
    try:
        rr = review_service.reject_listing(db, pipeline_run_id, ranking_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return RankingResponse.model_validate(rr)
