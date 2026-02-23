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


async def run_pipeline(
    db: Session, transcript_id: int, llm: LLMProvider
) -> PipelineRun:
    transcript = (
        db.query(Transcript).filter(Transcript.id == transcript_id).first()
    )
    if not transcript:
        raise TranscriptNotFoundError(f"Transcript {transcript_id} not found")

    pipeline_run = PipelineRun(
        transcript_id=transcript_id,
        current_stage=PipelineStage.INGESTION.value,
        status=PipelineStatus.IN_PROGRESS.value,
    )
    db.add(pipeline_run)
    db.commit()
    db.refresh(pipeline_run)

    now = datetime.now(timezone.utc)

    try:
        # Stage 1: Ingestion (already done - transcript was uploaded)
        pipeline_run.ingestion_completed_at = now
        pipeline_run.current_stage = PipelineStage.EXTRACTION.value
        db.commit()

        # Stage 2: Extraction
        requirement = await extraction_service.extract_requirements(
            db, transcript_id, llm
        )
        pipeline_run.extraction_completed_at = datetime.now(timezone.utc)
        pipeline_run.current_stage = PipelineStage.SEARCH.value
        db.commit()

        # Stage 3: Search
        listings = await search_service.search_listings(
            db, requirement.id, pipeline_run_id=pipeline_run.id
        )
        pipeline_run.search_completed_at = datetime.now(timezone.utc)
        pipeline_run.current_stage = PipelineStage.RANKING.value
        db.commit()

        # Stage 4: Ranking
        await ranking_service.rank_results(
            db=db,
            pipeline_run_id=pipeline_run.id,
            requirement=requirement,
            listings=listings,
            llm=llm,
        )
        pipeline_run.ranking_completed_at = datetime.now(timezone.utc)
        pipeline_run.current_stage = PipelineStage.REVIEW.value
        db.commit()

        # Stage 5: Review - pause here for human-in-the-loop
        pipeline_run.status = PipelineStatus.COMPLETED.value
        db.commit()

    except Exception as e:
        logger.exception("Pipeline failed at stage %s", pipeline_run.current_stage)
        pipeline_run.status = PipelineStatus.FAILED.value
        pipeline_run.error_message = str(e)
        db.commit()

    db.refresh(pipeline_run)
    return pipeline_run


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
