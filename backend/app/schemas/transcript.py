from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
