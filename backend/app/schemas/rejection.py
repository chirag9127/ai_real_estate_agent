from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RejectRequest(BaseModel):
    reason: str  # one of the predefined keys
    details: str | None = None  # free text for "other"


class RejectionReasonResponse(BaseModel):
    id: int
    ranked_result_id: int
    reason: str
    details: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
