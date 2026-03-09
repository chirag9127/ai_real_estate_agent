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
    property_types: list[str]
    min_beds: int | None
    min_baths: int | None
    min_sqft: int | None
    min_full_baths: int | None
    min_total_baths: int | None
    min_total_parking: int | None
    min_garage_spaces: int | None
    garage_type: str | None
    basement_required: bool | None
    basement_finished: bool | None
    basement_separate_entrance: bool | None
    basement_legal_suite: bool | None
    city: str | None
    sub_area: str | None
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
                "min_full_baths",
                "min_total_baths",
                "min_total_parking",
                "min_garage_spaces",
                "garage_type",
                "basement_required",
                "basement_finished",
                "basement_separate_entrance",
                "basement_legal_suite",
                "city",
                "sub_area",
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
            for field in ["locations", "must_haves", "nice_to_haves", "property_types"]:
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
    property_types: list[str] | None = None
    min_beds: int | None = None
    min_baths: int | None = None
    min_sqft: int | None = None
    min_full_baths: int | None = None
    min_total_baths: int | None = None
    min_total_parking: int | None = None
    min_garage_spaces: int | None = None
    garage_type: str | None = None
    basement_required: bool | None = None
    basement_finished: bool | None = None
    basement_separate_entrance: bool | None = None
    basement_legal_suite: bool | None = None
    city: str | None = None
    sub_area: str | None = None
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
    property_types: list[str] = []
    min_beds: int = 0
    min_baths: int = 0
    min_sqft: int = 0
    min_full_baths: int = 0
    min_total_baths: int = 0
    min_total_parking: int = 0
    min_garage_spaces: int = 0
    garage_type: str = ""
    basement_required: bool = False
    basement_finished: bool = False
    basement_separate_entrance: bool = False
    basement_legal_suite: bool = False
    city: str = ""
    sub_area: str = ""
    school_requirement: str = ""
    timeline: str = ""
    financing_type: str = ""
    confidence_score: float = 0.0
