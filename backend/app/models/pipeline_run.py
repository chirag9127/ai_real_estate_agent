from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.transcript import Transcript


class PipelineStage(StrEnum):
    INGESTION = "ingestion"
    EXTRACTION = "extraction"
    SEARCH = "search"
    RANKING = "ranking"
    REVIEW = "review"
    SEND = "send"


class PipelineStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transcript_id: Mapped[int] = mapped_column(
        ForeignKey("transcripts.id"), nullable=False
    )
    current_stage: Mapped[str] = mapped_column(
        String(20), default=PipelineStage.INGESTION.value
    )
    status: Mapped[str] = mapped_column(
        String(20), default=PipelineStatus.PENDING.value
    )

    ingestion_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    extraction_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    search_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    ranking_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    review_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    send_completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    transcript: Mapped["Transcript"] = relationship(back_populates="pipeline_runs")
