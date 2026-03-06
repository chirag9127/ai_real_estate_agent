from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EmailSendResponse(BaseModel):
    id: int
    pipeline_run_id: int
    recipient_email: str
    tone: str
    subject: str
    sent_at: datetime | None = None
    client_feedback: str | None = None
    client_feedback_at: datetime | None = None
    status: str = "sent"

    model_config = {"from_attributes": True}


class FeedbackRequest(BaseModel):
    feedback: str  # interested, not_interested, need_more_info, scheduled_viewing
