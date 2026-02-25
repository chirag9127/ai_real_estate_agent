from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, model_validator


class RequirementResponse(BaseModel):
    id: int
    transcript_id: int
    client_id: int | None
    client_name: str | None
    budget_max: float | None
    locations: list[str]
    must_haves: list[str]
    nice_to_haves: list[str]
    property_type: str | None
    min_beds: int | None
    min_baths: int | None
    min_sqft: int | None
    school_requirement: str | None
    timeline: str | None
    financing_type: str | None
    confidence_score: float | None
    llm_provider: str | None
    llm_model: str | None
    is_edited: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            obj = data
            result = {}
            for field in [
                "id",
                "transcript_id",
                "client_id",
                "client_name",
                "budget_max",
                "property_type",
                "min_beds",
                "min_baths",
                "min_sqft",
                "school_requirement",
                "timeline",
                "financing_type",
                "confidence_score",
                "llm_provider",
                "llm_model",
                "is_edited",
                "created_at",
                "updated_at",
            ]:
                result[field] = getattr(obj, field, None)
            for field in ["locations", "must_haves", "nice_to_haves"]:
                val = getattr(obj, field, None)
                result[field] = json.loads(val) if isinstance(val, str) else (val or [])
            return result
        return data


class RequirementUpdate(BaseModel):
    client_name: str | None = None
    budget_max: float | None = None
    locations: list[str] | None = None
    must_haves: list[str] | None = None
    nice_to_haves: list[str] | None = None
    property_type: str | None = None
    min_beds: int | None = None
    min_baths: int | None = None
    min_sqft: int | None = None
    school_requirement: str | None = None
    timeline: str | None = None
    financing_type: str | None = None


class LLMExtractionResult(BaseModel):
    client_name: str = ""
    budget_max: float = 0
    locations: list[str] = []
    must_haves: list[str] = []
    nice_to_haves: list[str] = []
    property_type: str = ""
    min_beds: int = 0
    min_baths: int = 0
    min_sqft: int = 0
    school_requirement: str = ""
    timeline: str = ""
    financing_type: str = ""
    confidence_score: float = 0.0
