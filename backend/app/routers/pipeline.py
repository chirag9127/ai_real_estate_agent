from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.schemas.pipeline import PipelineRunResponse
from app.services import pipeline_service
from app.utils.exceptions import PipelineRunNotFoundError, TranscriptNotFoundError

router = APIRouter(prefix="/pipeline")


@router.post("/start/{transcript_id}", response_model=PipelineRunResponse)
def start_pipeline(
    transcript_id: int,
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    try:
        run = pipeline_service.start_pipeline(db, transcript_id)
        return PipelineRunResponse.model_validate(run)
    except TranscriptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{run_id}/extract", response_model=PipelineRunResponse)
async def run_extraction(
    run_id: int,
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> PipelineRunResponse:
    try:
        run = await pipeline_service.run_extraction_step(db, run_id, llm)
        return PipelineRunResponse.model_validate(run)
    except PipelineRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{run_id}/search", response_model=PipelineRunResponse)
async def run_search(
    run_id: int,
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    try:
        run = await pipeline_service.run_search_step(db, run_id)
        return PipelineRunResponse.model_validate(run)
    except PipelineRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{run_id}/rank", response_model=PipelineRunResponse)
async def run_ranking(
    run_id: int,
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> PipelineRunResponse:
    try:
        run = await pipeline_service.run_ranking_step(db, run_id, llm)
        return PipelineRunResponse.model_validate(run)
    except PipelineRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/{run_id}", response_model=PipelineRunResponse)
def get_pipeline_run(
    run_id: int, db: Session = Depends(get_db)
) -> PipelineRunResponse:
    try:
        run = pipeline_service.get_pipeline_run(db, run_id)
        return PipelineRunResponse.model_validate(run)
    except PipelineRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("", response_model=list[PipelineRunResponse])
def list_pipeline_runs(
    skip: int = 0, limit: int = 20, db: Session = Depends(get_db)
) -> list[PipelineRunResponse]:
    runs = pipeline_service.list_pipeline_runs(db, skip, limit)
    return [PipelineRunResponse.model_validate(r) for r in runs]
