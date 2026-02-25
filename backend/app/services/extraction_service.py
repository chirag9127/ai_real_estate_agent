from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.models.requirement import ExtractedRequirement
from app.models.transcript import Transcript
from app.schemas.requirement import LLMExtractionResult
from app.utils.exceptions import ExtractionError, TranscriptNotFoundError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


async def extract_requirements(
    db: Session, transcript_id: int, llm: LLMProvider
) -> ExtractedRequirement:
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise TranscriptNotFoundError(f"Transcript {transcript_id} not found")

    transcript.status = "extracting"
    db.commit()

    try:
        raw_result = await llm.extract_requirements(transcript.raw_text)
        parsed = LLMExtractionResult(**raw_result)

        existing = (
            db.query(ExtractedRequirement)
            .filter(ExtractedRequirement.transcript_id == transcript_id)
            .first()
        )

        if existing:
            requirement = existing
        else:
            requirement = ExtractedRequirement(transcript_id=transcript_id)
            db.add(requirement)

        requirement.client_name = parsed.client_name
        requirement.budget_max = parsed.budget_max
        requirement.locations = json.dumps(parsed.locations)
        requirement.must_haves = json.dumps(parsed.must_haves)
        requirement.nice_to_haves = json.dumps(parsed.nice_to_haves)
        requirement.property_type = parsed.property_type
        requirement.min_beds = parsed.min_beds
        requirement.min_baths = parsed.min_baths
        requirement.min_sqft = parsed.min_sqft
        requirement.school_requirement = parsed.school_requirement
        requirement.timeline = parsed.timeline
        requirement.financing_type = parsed.financing_type
        requirement.confidence_score = parsed.confidence_score
        requirement.llm_provider = llm.provider_name
        requirement.llm_model = llm.model_name
        requirement.raw_llm_response = json.dumps(raw_result)

        transcript.status = "extracted"
        db.commit()
        db.refresh(requirement)
        return requirement

    except Exception as e:
        logger.exception("Extraction failed for transcript %s", transcript_id)
        transcript.status = "failed"
        db.commit()
        raise ExtractionError(f"Extraction failed: {e}") from e


def get_requirement(db: Session, requirement_id: int) -> ExtractedRequirement | None:
    return (
        db.query(ExtractedRequirement)
        .filter(ExtractedRequirement.id == requirement_id)
        .first()
    )


def get_requirement_by_transcript(
    db: Session, transcript_id: int
) -> ExtractedRequirement | None:
    return (
        db.query(ExtractedRequirement)
        .filter(ExtractedRequirement.transcript_id == transcript_id)
        .first()
    )


def update_requirement(
    db: Session, requirement_id: int, updates: dict
) -> ExtractedRequirement:
    requirement = get_requirement(db, requirement_id)
    if not requirement:
        raise TranscriptNotFoundError(f"Requirement {requirement_id} not found")

    for key, value in updates.items():
        if value is not None:
            if key in ("locations", "must_haves", "nice_to_haves"):
                setattr(requirement, key, json.dumps(value))
            else:
                setattr(requirement, key, value)

    requirement.is_edited = True
    db.commit()
    db.refresh(requirement)
    return requirement
