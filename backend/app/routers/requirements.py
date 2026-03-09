from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.llm.factory import get_llm_provider
from app.schemas.requirement import RequirementResponse, RequirementUpdate
from app.services import extraction_service
from app.utils.exceptions import ExtractionError, TranscriptNotFoundError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.llm.base import LLMProvider

router = APIRouter()


@router.post("/transcripts/{transcript_id}/extract", response_model=RequirementResponse)
async def extract_requirements(
    transcript_id: int,
    db: Session = Depends(get_db),
    llm: LLMProvider = Depends(get_llm_provider),
) -> RequirementResponse:
    try:
        requirement = await extraction_service.extract_requirements(
            db, transcript_id, llm
        )
        return RequirementResponse.model_validate(requirement)
    except TranscriptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ExtractionError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/requirements/{requirement_id}", response_model=RequirementResponse)
def get_requirement(
    requirement_id: int, db: Session = Depends(get_db)
) -> RequirementResponse:
    requirement = extraction_service.get_requirement(db, requirement_id)
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return RequirementResponse.model_validate(requirement)


@router.get(
    "/transcripts/{transcript_id}/requirements", response_model=RequirementResponse
)
def get_requirement_by_transcript(
    transcript_id: int, db: Session = Depends(get_db)
) -> RequirementResponse:
    requirement = extraction_service.get_requirement_by_transcript(db, transcript_id)
    if not requirement:
        raise HTTPException(
            status_code=404, detail="No requirements found for this transcript"
        )
    return RequirementResponse.model_validate(requirement)


@router.put("/requirements/{requirement_id}", response_model=RequirementResponse)
def update_requirement(
    requirement_id: int,
    body: RequirementUpdate,
    db: Session = Depends(get_db),
) -> RequirementResponse:
    try:
        requirement = extraction_service.update_requirement(
            db, requirement_id, body.model_dump(exclude_unset=True)
        )
        return RequirementResponse.model_validate(requirement)
    except TranscriptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
