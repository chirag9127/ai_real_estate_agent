from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# Predefined reason keys
REJECTION_REASON_KEYS = [
    "location_mismatch",
    "overpriced",
    "lot_too_small",
    "layout_inefficient",
    "not_enough_light",
    "basement_issue",
    "other",
]


class RejectionReason(Base):
    """Stores a structured rejection reason for a ranked listing."""

    __tablename__ = "rejection_reasons"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ranked_result_id: Mapped[int] = mapped_column(
        ForeignKey("ranked_results.id"), nullable=False
    )
    pipeline_run_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_runs.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
