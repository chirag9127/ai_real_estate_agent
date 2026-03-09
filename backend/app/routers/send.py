from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.schemas.email_send import EmailSendResponse, FeedbackRequest
from app.services import send_service

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

router = APIRouter(prefix="/send")


class SendEmailRequest(BaseModel):
    recipient_email: str
    tone: str = "professional"  # "professional", "casual", "advisory"
    subject: str | None = None  # custom subject override
    body: str | None = None  # custom body text override
    agent_name: str = "Harry"
    agent_phone: str = ""
    agent_email: str = ""
    brokerage_name: str = ""


class PreviewRequest(BaseModel):
    tone: str = "professional"
    subject: str | None = None
    body: str | None = None
    agent_name: str = "Harry"
    agent_phone: str = ""
    agent_email: str = ""
    brokerage_name: str = ""


@router.get("/templates")
def list_templates() -> list[dict]:
    return send_service.get_email_templates()


@router.post("/{pipeline_run_id}/preview")
def preview(
    pipeline_run_id: int,
    body: PreviewRequest,
    db: Session = Depends(get_db),
) -> dict:
    return send_service.preview_email(
        db,
        pipeline_run_id,
        tone=body.tone,
        subject=body.subject,
        body=body.body,
        agent_name=body.agent_name,
        agent_phone=body.agent_phone,
        agent_email=body.agent_email,
        brokerage_name=body.brokerage_name,
    )


@router.post("/{pipeline_run_id}")
def send_to_client(
    pipeline_run_id: int,
    body: SendEmailRequest,
    db: Session = Depends(get_db),
) -> dict:
    return send_service.send_email(
        db,
        pipeline_run_id,
        body.recipient_email,
        tone=body.tone,
        subject_override=body.subject,
        body_override=body.body,
        agent_name=body.agent_name,
        agent_phone=body.agent_phone,
        agent_email=body.agent_email,
        brokerage_name=body.brokerage_name,
    )


@router.get("/status/{pipeline_run_id}")
def get_send_status(
    pipeline_run_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return send_service.get_send_status(db, pipeline_run_id)


@router.get("/{pipeline_run_id}/history", response_model=list[EmailSendResponse])
def get_email_history(
    pipeline_run_id: int,
    db: Session = Depends(get_db),
) -> list:
    return send_service.get_email_history(db, pipeline_run_id)


@router.post("/feedback/{send_id}", response_model=EmailSendResponse)
def submit_feedback(
    send_id: int,
    body: FeedbackRequest,
    db: Session = Depends(get_db),
) -> EmailSendResponse:
    if body.feedback not in send_service.VALID_FEEDBACK_VALUES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feedback. Must be one of: {', '.join(sorted(send_service.VALID_FEEDBACK_VALUES))}",
        )
    result = send_service.record_feedback(db, send_id, body.feedback)
    if not result:
        raise HTTPException(status_code=404, detail="Email send record not found.")
    return result
