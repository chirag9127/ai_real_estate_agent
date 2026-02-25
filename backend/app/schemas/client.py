from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import datetime


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
