from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.llm.base import LLMProvider
from app.models.pipeline_run import PipelineRun, PipelineStage, PipelineStatus
from app.models.transcript import Transcript
from app.services import extraction_service, ranking_service, search_service
from app.utils.exceptions import PipelineRunNotFoundError, TranscriptNotFoundError

logger = logging.getLogger(__name__)


def start_pipeline(db: Session, transcript_id: int) -> PipelineRun:
    """Create a pipeline run and mark ingestion as complete."""
    transcript = (
        db.query(Transcript).filter(Transcript.id == transcript_id).first()
    )
    if not transcript:
        raise TranscriptNotFoundError(f"Transcript {transcript_id} not found")

    pipeline_run = PipelineRun(
        transcript_id=transcript_id,
        current_stage=PipelineStage.EXTRACTION.value,
        status=PipelineStatus.IN_PROGRESS.value,
        ingestion_completed_at=datetime.now(timezone.utc),
    )
    db.add(pipeline_run)
    db.commit()
    db.refresh(pipeline_run)
    return pipeline_run


async def run_extraction_step(
    db: Session, run_id: int, llm: LLMProvider
) -> PipelineRun:
    """Run just the extraction stage of the pipeline."""
    pipeline_run = _get_run_or_raise(db, run_id)
    try:
        await extraction_service.extract_requirements(
            db, pipeline_run.transcript_id, llm
        )
        pipeline_run.extraction_completed_at = datetime.now(timezone.utc)
        pipeline_run.current_stage = PipelineStage.SEARCH.value
        db.commit()
    except Exception as e:
        logger.exception("Pipeline failed at extraction")
        pipeline_run.status = PipelineStatus.FAILED.value
        pipeline_run.error_message = str(e)
        db.commit()
    db.refresh(pipeline_run)
    return pipeline_run


async def run_search_step(db: Session, run_id: int) -> PipelineRun:
    """Run just the search stage of the pipeline."""
    pipeline_run = _get_run_or_raise(db, run_id)
    requirement = (
        db.query(extraction_service.ExtractedRequirement)
        .filter(
            extraction_service.ExtractedRequirement.transcript_id
            == pipeline_run.transcript_id
        )
        .first()
    )
    if not requirement:
        pipeline_run.status = PipelineStatus.FAILED.value
        pipeline_run.error_message = "No extracted requirement found"
        db.commit()
        db.refresh(pipeline_run)
        return pipeline_run

    try:
        await search_service.search_listings(
            db, requirement.id, pipeline_run_id=pipeline_run.id
        )
        pipeline_run.search_completed_at = datetime.now(timezone.utc)
        pipeline_run.current_stage = PipelineStage.RANKING.value
        db.commit()
    except Exception as e:
        logger.exception("Pipeline failed at search")
        pipeline_run.status = PipelineStatus.FAILED.value
        pipeline_run.error_message = str(e)
        db.commit()
    db.refresh(pipeline_run)
    return pipeline_run


async def run_ranking_step(
    db: Session, run_id: int, llm: LLMProvider
) -> PipelineRun:
    """Run just the ranking stage of the pipeline."""
    from app.models.listing import Listing

    pipeline_run = _get_run_or_raise(db, run_id)
    requirement = (
        db.query(extraction_service.ExtractedRequirement)
        .filter(
            extraction_service.ExtractedRequirement.transcript_id
            == pipeline_run.transcript_id
        )
        .first()
    )
    listings = (
        db.query(Listing)
        .filter(Listing.pipeline_run_id == pipeline_run.id)
        .all()
    )

    if not requirement or not listings:
        pipeline_run.status = PipelineStatus.FAILED.value
        pipeline_run.error_message = "Missing requirement or listings for ranking"
        db.commit()
        db.refresh(pipeline_run)
        return pipeline_run

    try:
        await ranking_service.rank_results(
            db=db,
            pipeline_run_id=pipeline_run.id,
            requirement=requirement,
            listings=listings,
            llm=llm,
        )
        pipeline_run.ranking_completed_at = datetime.now(timezone.utc)
        pipeline_run.current_stage = PipelineStage.REVIEW.value
        pipeline_run.status = PipelineStatus.COMPLETED.value
        db.commit()
    except Exception as e:
        logger.exception("Pipeline failed at ranking")
        pipeline_run.status = PipelineStatus.FAILED.value
        pipeline_run.error_message = str(e)
        db.commit()
    db.refresh(pipeline_run)
    return pipeline_run


def _get_run_or_raise(db: Session, run_id: int) -> PipelineRun:
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise PipelineRunNotFoundError(f"Pipeline run {run_id} not found")
    return run


def get_pipeline_run(db: Session, run_id: int) -> PipelineRun:
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise PipelineRunNotFoundError(f"Pipeline run {run_id} not found")
    return run


def list_pipeline_runs(
    db: Session, skip: int = 0, limit: int = 20
) -> list[PipelineRun]:
    return (
        db.query(PipelineRun)
        .order_by(PipelineRun.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
