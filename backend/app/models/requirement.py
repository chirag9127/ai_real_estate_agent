import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.client import Client
    from app.models.transcript import Transcript


class ExtractedRequirement(Base):
    __tablename__ = "extracted_requirements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transcript_id: Mapped[int] = mapped_column(
        ForeignKey("transcripts.id"), unique=True, nullable=False
    )
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id"), nullable=True
    )

    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    locations: Mapped[str | None] = mapped_column(Text, nullable=True)
    must_haves: Mapped[str | None] = mapped_column(Text, nullable=True)
    nice_to_haves: Mapped[str | None] = mapped_column(Text, nullable=True)
    property_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    min_beds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_baths: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    school_requirement: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timeline: Mapped[str | None] = mapped_column(String(255), nullable=True)
    financing_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    transcript: Mapped["Transcript"] = relationship(back_populates="requirement")
    client: Mapped[Optional["Client"]] = relationship(back_populates="requirements")

    @property
    def locations_list(self) -> list[str]:
        return json.loads(self.locations) if self.locations else []

    @property
    def must_haves_list(self) -> list[str]:
        return json.loads(self.must_haves) if self.must_haves else []

    @property
    def nice_to_haves_list(self) -> list[str]:
        return json.loads(self.nice_to_haves) if self.nice_to_haves else []
