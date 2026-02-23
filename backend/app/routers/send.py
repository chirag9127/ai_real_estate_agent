from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import send_service

router = APIRouter(prefix="/send")


class SendEmailRequest(BaseModel):
    recipient_email: str


@router.post("/{pipeline_run_id}")
def send_to_client(
    pipeline_run_id: int,
    body: SendEmailRequest,
    db: Session = Depends(get_db),
) -> dict:
    return send_service.send_email(db, pipeline_run_id, body.recipient_email)


@router.get("/status/{pipeline_run_id}")
def get_send_status(
    pipeline_run_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return send_service.get_send_status(db, pipeline_run_id)
