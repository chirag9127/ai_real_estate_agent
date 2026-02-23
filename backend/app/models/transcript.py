from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.pipeline_run import PipelineRun
    from app.models.requirement import ExtractedRequirement


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("clients.id"), nullable=True
    )
    filename: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    upload_method: Mapped[str] = mapped_column(String(20), default="file")
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    client: Mapped[Optional["Client"]] = relationship(back_populates="transcripts")
    requirement: Mapped[Optional["ExtractedRequirement"]] = relationship(
        back_populates="transcript", uselist=False
    )
    pipeline_runs: Mapped[list["PipelineRun"]] = relationship(
        back_populates="transcript"
    )
