from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.transcript import Transcript
from app.schemas.transcript import TranscriptResponse
from app.services import google_docs_service

router = APIRouter(prefix="/google")


# ── Request / Response schemas ──────────────────────────────────


class AuthUrlResponse(BaseModel):
    auth_url: str


class CallbackRequest(BaseModel):
    code: str


class DocImportRequest(BaseModel):
    credentials: dict
    document_id: str


class DocListRequest(BaseModel):
    credentials: dict


class GoogleDocItem(BaseModel):
    id: str
    name: str
    modifiedTime: str


# ── Endpoints ───────────────────────────────────────────────────


@router.get("/auth-url", response_model=AuthUrlResponse)
def google_auth_url() -> AuthUrlResponse:
    """Return the Google OAuth 2.0 authorization URL."""
    try:
        url = google_docs_service.get_auth_url()
        return AuthUrlResponse(auth_url=url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/callback")
def google_callback(body: CallbackRequest) -> dict:
    """Exchange authorization code for credentials."""
    try:
        credentials = google_docs_service.exchange_code(body.code)
        return {"credentials": credentials}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/docs", response_model=TranscriptResponse)
def import_google_doc(
    body: DocImportRequest, db: Session = Depends(get_db)
) -> TranscriptResponse:
    """Fetch a Google Doc and create a Transcript record."""
    try:
        text = google_docs_service.fetch_document_text(
            body.credentials, body.document_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    transcript = Transcript(
        filename=f"google-doc-{body.document_id}",
        raw_text=text,
        upload_method="google_docs",
        status="uploaded",
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return TranscriptResponse.model_validate(transcript)


@router.post("/docs/list", response_model=list[GoogleDocItem])
def list_google_docs(body: DocListRequest) -> list[GoogleDocItem]:
    """List recent Google Docs the user has access to."""
    try:
        docs = google_docs_service.list_recent_docs(body.credentials)
        return [GoogleDocItem(**d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
