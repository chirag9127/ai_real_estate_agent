"""WhatsApp webhook router -- receives Twilio webhook POSTs and exposes
a small management API for the frontend dashboard."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.config import settings
from app.database import get_db
from app.services import whatsapp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp")


# ---------------------------------------------------------------------------
# Twilio signature validation
# ---------------------------------------------------------------------------


def _validate_twilio_signature(request: Request, form: dict[str, str]) -> bool:
    """Verify the X-Twilio-Signature header using the Twilio auth token.

    Returns True when validation passes **or** when Twilio credentials are
    not configured (development / sandbox mode).
    """
    if not settings.twilio_auth_token:
        # No auth token configured -- skip validation (dev mode)
        return True

    signature = request.headers.get("X-Twilio-Signature", "")
    # Reconstruct the full URL that Twilio used to compute the signature
    url = str(request.url)
    validator = RequestValidator(settings.twilio_auth_token)
    return validator.validate(url, form, signature)


# ---------------------------------------------------------------------------
# Twilio webhook endpoint
# ---------------------------------------------------------------------------


@router.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    """Receive an incoming WhatsApp message from Twilio.

    Twilio sends form-encoded POST data with fields such as:
      - Body: the message text
      - From: sender number (e.g. whatsapp:+1234567890)
      - To: your Twilio number
      - ProfileName: WhatsApp display name
      - WaId: WhatsApp user ID
      - NumMedia: number of media attachments
      - MessageSid: unique message identifier
    """
    form = dict(await request.form())

    # Validate the request actually came from Twilio
    if not _validate_twilio_signature(request, form):
        logger.warning("Invalid Twilio signature -- rejecting request")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    from_number: str = form.get("From", "")
    body: str = form.get("Body", "")
    profile_name: str | None = form.get("ProfileName")

    logger.info(
        "WhatsApp webhook from=%s profile=%s body=%s",
        from_number,
        profile_name,
        body[:80] if body else "",
    )

    reply_text, pipeline_run_id = whatsapp_service.handle_incoming_message(
        db,
        from_number=from_number,
        body=body,
        profile_name=profile_name,
    )

    # If a new pipeline was created, schedule it to run in the background
    if pipeline_run_id is not None:
        whatsapp_service.schedule_pipeline(pipeline_run_id, from_number)

    # Return TwiML response so Twilio sends the reply back to the user
    twiml = MessagingResponse()
    twiml.message(reply_text)
    return Response(content=str(twiml), media_type="text/xml")


# ---------------------------------------------------------------------------
# Management / dashboard API
# ---------------------------------------------------------------------------


class SendResultsRequest(BaseModel):
    to_number: str
    pipeline_run_id: int


class SendMessageRequest(BaseModel):
    to_number: str
    message: str


@router.get("/conversations")
def list_conversations() -> dict:
    """Return active WhatsApp conversations (sender -> pipeline_run_id)."""
    return {
        "conversations": whatsapp_service.get_active_conversations(),
    }


@router.post("/send-results")
def send_results(
    body: SendResultsRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Manually send pipeline results to a WhatsApp number."""
    return whatsapp_service.send_pipeline_results(
        db, body.pipeline_run_id, body.to_number
    )


@router.post("/send-message")
def send_message(body: SendMessageRequest) -> dict:
    """Send an arbitrary WhatsApp message (useful for testing)."""
    return whatsapp_service.send_whatsapp_message(body.to_number, body.message)


@router.get("/status/{from_number:path}")
def get_status(
    from_number: str,
    db: Session = Depends(get_db),
) -> dict:
    """Get the pipeline status for a given WhatsApp sender."""
    msg = whatsapp_service.get_pipeline_status_message(db, from_number)
    if msg is None:
        return {"from_number": from_number, "status": "no_active_pipeline"}
    return {"from_number": from_number, "status": msg}
