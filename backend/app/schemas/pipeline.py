from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import datetime


class PipelineRunResponse(BaseModel):
    id: int
    transcript_id: int
    current_stage: str
    status: str
    ingestion_completed_at: datetime | None
    extraction_completed_at: datetime | None
    search_completed_at: datetime | None
    ranking_completed_at: datetime | None
    review_completed_at: datetime | None
    send_completed_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
