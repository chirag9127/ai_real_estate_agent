from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.listing import Listing


class RankedResult(Base):
    """Ranked listing result with score breakdown."""

    __tablename__ = "ranked_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pipeline_run_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_runs.id"), nullable=False
    )
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id"), nullable=False
    )
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("extracted_requirements.id"), nullable=False
    )
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    must_have_pass: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    nice_to_have_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rank_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_breakdown_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by_harry: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    sent_to_client: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    listing: Mapped[Listing] = relationship(lazy="joined")

    @property
    def score_breakdown(self) -> dict[str, Any] | None:
        if self.score_breakdown_json:
            return json.loads(self.score_breakdown_json)
        return None
