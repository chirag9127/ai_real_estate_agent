"""Review workflow: fetch ranked listings for approval, approve/reject."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.models.pipeline_run import PipelineRun
from app.models.ranking import RankedResult
from app.models.rejection import RejectionReason

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_pending_review(db: Session, pipeline_run_id: int) -> list[RankedResult]:
    """Return all ranked results for a pipeline run, ordered by rank position."""
    return (
        db.query(RankedResult)
        .filter(RankedResult.pipeline_run_id == pipeline_run_id)
        .order_by(RankedResult.rank_position.asc())
        .all()
    )


def approve_listings(
    db: Session, pipeline_run_id: int, ranking_ids: list[int]
) -> list[RankedResult]:
    """Mark selected rankings as approved, the rest as rejected.

    Returns the full updated list of ranked results.
    """
    all_rankings = (
        db.query(RankedResult)
        .filter(RankedResult.pipeline_run_id == pipeline_run_id)
        .all()
    )

    approved_set = set(ranking_ids)
    for rr in all_rankings:
        rr.approved_by_harry = rr.id in approved_set

    # Mark the review stage as completed on the pipeline run
    pipeline_run = (
        db.query(PipelineRun).filter(PipelineRun.id == pipeline_run_id).first()
    )
    if pipeline_run:
        pipeline_run.review_completed_at = datetime.now(timezone.utc)

    db.commit()
    for rr in all_rankings:
        db.refresh(rr)

    approved_count = sum(1 for rr in all_rankings if rr.approved_by_harry)
    logger.info(
        "Review complete for pipeline_run_id=%d: %d/%d approved",
        pipeline_run_id,
        approved_count,
        len(all_rankings),
    )
    return sorted(all_rankings, key=lambda r: r.rank_position or 0)


def reject_listing(
    db: Session,
    pipeline_run_id: int,
    ranking_id: int,
    reason: str,
    details: str | None = None,
) -> RankedResult:
    """Mark a single ranking as rejected with a structured reason."""
    rr = (
        db.query(RankedResult)
        .filter(
            RankedResult.pipeline_run_id == pipeline_run_id,
            RankedResult.id == ranking_id,
        )
        .first()
    )
    if not rr:
        raise ValueError(
            f"Ranking {ranking_id} not found for pipeline run {pipeline_run_id}"
        )

    rr.approved_by_harry = False
    rr.rejection_reason = reason
    rr.rejection_details = details

    # Create a RejectionReason record for history
    rejection = RejectionReason(
        ranked_result_id=ranking_id,
        pipeline_run_id=pipeline_run_id,
        reason=reason,
        details=details,
    )
    db.add(rejection)

    db.commit()
    db.refresh(rr)
    logger.info(
        "Rejected ranking_id=%d (pipeline_run_id=%d) reason=%s",
        ranking_id,
        pipeline_run_id,
        reason,
    )
    return rr


def get_rejections(db: Session, pipeline_run_id: int) -> list[RejectionReason]:
    """Return all rejection reasons for a pipeline run."""
    return (
        db.query(RejectionReason)
        .filter(RejectionReason.pipeline_run_id == pipeline_run_id)
        .order_by(RejectionReason.created_at.desc())
        .all()
    )
