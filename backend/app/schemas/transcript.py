from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import datetime


class TranscriptPaste(BaseModel):
    text: str
    client_name: str | None = None


class TranscriptResponse(BaseModel):
    id: int
    client_id: int | None
    filename: str | None
    raw_text: str
    upload_method: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptListResponse(BaseModel):
    id: int
    client_id: int | None
    filename: str | None
    upload_method: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
