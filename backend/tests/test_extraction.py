"""Unit tests for extraction prompt, LLMExtractionResult schema, and extraction service."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock

import pytest

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.llm.prompts.extraction import EXTRACTION_SYSTEM_PROMPT  # noqa: E402
from app.schemas.requirement import LLMExtractionResult  # noqa: E402
from app.services.extraction_service import update_requirement  # noqa: E402


# ---------------------------------------------------------------------------
# LLMExtractionResult parsing tests
# ---------------------------------------------------------------------------

class TestLLMExtractionResult:
    """Verify LLMExtractionResult can parse a complete JSON response with all fields."""

    def test_parse_complete_response(self):
        raw = {
            "client_name": "John Doe",
            "budget_max": 800000,
            "locations": ["Mississauga", "Brampton"],
            "must_haves": ["3 bedrooms", "garage"],
            "nice_to_haves": ["pool", "finished basement"],
            "property_type": "house",
            "property_types": ["Detached", "Semi-detached"],
            "min_beds": 3,
            "min_baths": 2,
            "min_sqft": 1500,
            "min_full_baths": 2,
            "min_total_baths": 3,
            "min_total_parking": 2,
            "min_garage_spaces": 1,
            "garage_type": "attached",
            "basement_required": True,
            "basement_finished": True,
            "basement_separate_entrance": False,
            "basement_legal_suite": False,
            "city": "Mississauga",
            "sub_area": "Erin Mills",
            "school_requirement": "good schools",
            "timeline": "3 months",
            "financing_type": "conventional",
            "confidence_score": 0.85,
        }
        parsed = LLMExtractionResult(**raw)

        assert parsed.client_name == "John Doe"
        assert parsed.budget_max == 800000
        assert parsed.locations == ["Mississauga", "Brampton"]
        assert parsed.must_haves == ["3 bedrooms", "garage"]
        assert parsed.nice_to_haves == ["pool", "finished basement"]
        assert parsed.property_type == "house"
        assert parsed.property_types == ["Detached", "Semi-detached"]
        assert parsed.min_beds == 3
        assert parsed.min_baths == 2
        assert parsed.min_sqft == 1500
        assert parsed.min_full_baths == 2
        assert parsed.min_total_baths == 3
        assert parsed.min_total_parking == 2
        assert parsed.min_garage_spaces == 1
        assert parsed.garage_type == "attached"
        assert parsed.basement_required is True
        assert parsed.basement_finished is True
        assert parsed.basement_separate_entrance is False
        assert parsed.basement_legal_suite is False
        assert parsed.city == "Mississauga"
        assert parsed.sub_area == "Erin Mills"
        assert parsed.school_requirement == "good schools"
        assert parsed.timeline == "3 months"
        assert parsed.financing_type == "conventional"
        assert parsed.confidence_score == 0.85

    def test_defaults_when_new_fields_missing(self):
        """New fields should default to 0/false/empty when not provided."""
        raw = {
            "client_name": "Jane",
            "budget_max": 500000,
            "locations": [],
            "must_haves": [],
            "nice_to_haves": [],
            "property_type": "condo",
            "min_beds": 2,
            "min_baths": 1,
            "min_sqft": 800,
            "school_requirement": "",
            "timeline": "",
            "financing_type": "",
            "confidence_score": 0.5,
        }
        parsed = LLMExtractionResult(**raw)

        assert parsed.property_types == []
        assert parsed.min_full_baths == 0
        assert parsed.min_total_baths == 0
        assert parsed.min_total_parking == 0
        assert parsed.min_garage_spaces == 0
        assert parsed.garage_type == ""
        assert parsed.basement_required is False
        assert parsed.basement_finished is False
        assert parsed.basement_separate_entrance is False
        assert parsed.basement_legal_suite is False
        assert parsed.city == ""
        assert parsed.sub_area == ""


# ---------------------------------------------------------------------------
# Extraction prompt tests
# ---------------------------------------------------------------------------

class TestExtractionPrompt:
    """Verify the extraction prompt contains all required field names."""

    REQUIRED_FIELDS = [
        "property_types",
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
    ]

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_prompt_contains_field(self, field):
        assert field in EXTRACTION_SYSTEM_PROMPT, (
            f"Field '{field}' not found in EXTRACTION_SYSTEM_PROMPT"
        )

    def test_prompt_contains_property_types_multiselect_rule(self):
        assert "multi-select" in EXTRACTION_SYSTEM_PROMPT

    def test_prompt_contains_city_subarea_rule(self):
        assert "city" in EXTRACTION_SYSTEM_PROMPT
        assert "sub_area" in EXTRACTION_SYSTEM_PROMPT

    def test_prompt_contains_basement_parking_defaults_rule(self):
        assert "default" in EXTRACTION_SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# update_requirement tests
# ---------------------------------------------------------------------------

class _FakeRequirement:
    """Simple object that records attribute assignments."""

    def __init__(self):
        self.id = 1
        self._assignments: dict[str, object] = {}

    def __setattr__(self, name: str, value: object) -> None:
        if name.startswith("_") or name == "id":
            super().__setattr__(name, value)
        else:
            self._assignments[name] = value
            super().__setattr__(name, value)


class TestUpdateRequirement:
    """Verify update_requirement correctly handles new fields including property_types."""

    def _make_mock_db_and_requirement(self):
        """Create mock db session and a fake requirement object."""
        requirement = _FakeRequirement()

        db = MagicMock()
        # Patch the query chain so get_requirement returns our fake
        db.query.return_value.filter.return_value.first.return_value = requirement
        return db, requirement

    def test_property_types_serialized_as_json(self):
        db, requirement = self._make_mock_db_and_requirement()
        updates = {"property_types": ["Detached", "Condo apartment"]}

        update_requirement(db, 1, updates)

        assert requirement.property_types == json.dumps(["Detached", "Condo apartment"])

    def test_scalar_fields_set_directly(self):
        db, requirement = self._make_mock_db_and_requirement()
        updates = {
            "min_full_baths": 2,
            "garage_type": "attached",
            "basement_required": True,
            "city": "Toronto",
            "sub_area": "North York",
        }

        update_requirement(db, 1, updates)

        for key, value in updates.items():
            assert getattr(requirement, key) == value, (
                f"Expected {key}={value}, got {getattr(requirement, key)}"
            )

    def test_locations_still_serialized_as_json(self):
        db, requirement = self._make_mock_db_and_requirement()
        updates = {"locations": ["Toronto", "Mississauga"]}

        update_requirement(db, 1, updates)

        assert requirement.locations == json.dumps(["Toronto", "Mississauga"])

    def test_none_values_skipped(self):
        db, requirement = self._make_mock_db_and_requirement()
        updates = {"city": None, "min_full_baths": None}

        update_requirement(db, 1, updates)

        # None values should be skipped, so they should not appear in assignments
        # (only is_edited should be set)
        assert "city" not in requirement._assignments
        assert "min_full_baths" not in requirement._assignments
        assert requirement._assignments.get("is_edited") is True
