from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.transcript import Transcript
from app.utils.exceptions import TranscriptNotFoundError
from app.utils.file_handling import read_upload_text, save_upload_file, validate_file

if TYPE_CHECKING:
    from fastapi import UploadFile
    from sqlalchemy.orm import Session


async def create_from_file(db: Session, file: UploadFile) -> Transcript:
    validate_file(file)
    await save_upload_file(file)
    text = await read_upload_text(file)

    transcript = Transcript(
        filename=file.filename,
        raw_text=text,
        upload_method="file",
        status="uploaded",
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript


def create_from_text(
    db: Session, text: str, client_name: str | None = None
) -> Transcript:
    transcript = Transcript(
        raw_text=text,
        upload_method="paste",
        status="uploaded",
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript


def get_transcript(db: Session, transcript_id: int) -> Transcript:
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise TranscriptNotFoundError(f"Transcript {transcript_id} not found")
    return transcript


def list_transcripts(db: Session, skip: int = 0, limit: int = 20) -> list[Transcript]:
    return (
        db.query(Transcript)
        .order_by(Transcript.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def delete_transcript(db: Session, transcript_id: int) -> bool:
    transcript = get_transcript(db, transcript_id)
    db.delete(transcript)
    db.commit()
    return True
