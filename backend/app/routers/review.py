from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.schemas.ranking import RankingResponse, RankingsListResponse
from app.schemas.rejection import RejectRequest, RejectionReasonResponse
from app.services import review_service

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

router = APIRouter(prefix="/review")

# Suggestions shown when no listings are approved
NO_APPROVAL_SUGGESTIONS = [
    "Adjust criteria",
    "Expand geography",
    "Increase budget",
    "Relax must-haves",
]


class ApproveRequest(BaseModel):
    ranking_ids: list[int]


class ReviewWithSuggestionsResponse(BaseModel):
    pipeline_run_id: int
    rankings: list[RankingResponse]
    total: int
    suggestions: list[str] = []


@router.get("/{pipeline_run_id}", response_model=ReviewWithSuggestionsResponse)
def get_pending_review(
    pipeline_run_id: int,
    db: Session = Depends(get_db),
) -> ReviewWithSuggestionsResponse:
    rankings = review_service.get_pending_review(db, pipeline_run_id)
    validated = [RankingResponse.model_validate(rr) for rr in rankings]
    approved_count = sum(1 for rr in rankings if rr.approved_by_harry)
    suggestions = NO_APPROVAL_SUGGESTIONS if approved_count == 0 else []
    return ReviewWithSuggestionsResponse(
        pipeline_run_id=pipeline_run_id,
        rankings=validated,
        total=len(validated),
        suggestions=suggestions,
    )


@router.post("/{pipeline_run_id}/approve", response_model=ReviewWithSuggestionsResponse)
def approve_listings(
    pipeline_run_id: int,
    body: ApproveRequest,
    db: Session = Depends(get_db),
) -> ReviewWithSuggestionsResponse:
    rankings = review_service.approve_listings(db, pipeline_run_id, body.ranking_ids)
    validated = [RankingResponse.model_validate(rr) for rr in rankings]
    approved_count = sum(1 for rr in rankings if rr.approved_by_harry)
    suggestions = NO_APPROVAL_SUGGESTIONS if approved_count == 0 else []
    return ReviewWithSuggestionsResponse(
        pipeline_run_id=pipeline_run_id,
        rankings=validated,
        total=len(validated),
        suggestions=suggestions,
    )


@router.post("/{pipeline_run_id}/reject/{ranking_id}", response_model=RankingResponse)
def reject_listing(
    pipeline_run_id: int,
    ranking_id: int,
    body: RejectRequest,
    db: Session = Depends(get_db),
) -> RankingResponse:
    try:
        rr = review_service.reject_listing(
            db, pipeline_run_id, ranking_id, body.reason, body.details
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return RankingResponse.model_validate(rr)


@router.get(
    "/{pipeline_run_id}/rejections",
    response_model=list[RejectionReasonResponse],
)
def get_rejections(
    pipeline_run_id: int,
    db: Session = Depends(get_db),
) -> list[RejectionReasonResponse]:
    reasons = review_service.get_rejections(db, pipeline_run_id)
    return [RejectionReasonResponse.model_validate(r) for r in reasons]
