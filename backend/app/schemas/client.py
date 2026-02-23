from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ClientCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None


class ClientResponse(BaseModel):
    id: int
    name: str
    email: str | None
    phone: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
