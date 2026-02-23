from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.transcript import (
    TranscriptListResponse,
    TranscriptPaste,
    TranscriptResponse,
)
from app.services import transcript_service
from app.utils.exceptions import TranscriptNotFoundError

router = APIRouter(prefix="/transcripts")


@router.post("/upload", response_model=TranscriptResponse)
async def upload_transcript(
    file: UploadFile, db: Session = Depends(get_db)
) -> TranscriptResponse:
    try:
        transcript = await transcript_service.create_from_file(db, file)
        return TranscriptResponse.model_validate(transcript)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/paste", response_model=TranscriptResponse)
def paste_transcript(
    body: TranscriptPaste, db: Session = Depends(get_db)
) -> TranscriptResponse:
    transcript = transcript_service.create_from_text(db, body.text, body.client_name)
    return TranscriptResponse.model_validate(transcript)


@router.get("", response_model=list[TranscriptListResponse])
def list_transcripts(
    skip: int = 0, limit: int = 20, db: Session = Depends(get_db)
) -> list[TranscriptListResponse]:
    transcripts = transcript_service.list_transcripts(db, skip, limit)
    return [TranscriptListResponse.model_validate(t) for t in transcripts]


@router.get("/{transcript_id}", response_model=TranscriptResponse)
def get_transcript(
    transcript_id: int, db: Session = Depends(get_db)
) -> TranscriptResponse:
    try:
        transcript = transcript_service.get_transcript(db, transcript_id)
        return TranscriptResponse.model_validate(transcript)
    except TranscriptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/{transcript_id}")
def delete_transcript(
    transcript_id: int, db: Session = Depends(get_db)
) -> dict:
    try:
        transcript_service.delete_transcript(db, transcript_id)
        return {"message": "Transcript deleted"}
    except TranscriptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
