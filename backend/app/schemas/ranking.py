from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.listing import ListingResponse


class RankingResponse(BaseModel):
    id: int
    listing: ListingResponse
    overall_score: float | None
    must_have_pass: bool | None
    nice_to_have_score: float | None
    rank_position: int | None
    score_breakdown: dict[str, Any] | None = None
    approved_by_harry: bool | None = None
    sent_to_client: bool = False

    model_config = {"from_attributes": True}


class RankingsListResponse(BaseModel):
    pipeline_run_id: int
    rankings: list[RankingResponse]
    total: int
