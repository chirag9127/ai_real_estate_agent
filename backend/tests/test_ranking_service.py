"""Unit tests for the ranking service.

Tests cover:
- Individual quantitative check functions
- The full async rank_results() pipeline with a mocked LLM
- Edge cases: empty listings, LLM failure, no semantic must-haves
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ranking_service import (
    _check_numeric,
    _check_property_type,
    _run_quantitative_checks,
    rank_results,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_listing(**overrides) -> MagicMock:
    """Create a mock Listing with sensible defaults."""
    defaults = dict(
        id=1,
        address="123 Main St",
        price=400_000,
        bedrooms=3,
        bathrooms=2.0,
        sqft=1800,
        property_type="house",
        description="Nice house",
        neighborhood="Downtown",
        year_built=2000,
        days_on_market=10,
    )
    defaults.update(overrides)
    listing = MagicMock()
    for k, v in defaults.items():
        setattr(listing, k, v)
    return listing


def _make_requirement(**overrides) -> MagicMock:
    """Create a mock ExtractedRequirement with sensible defaults."""
    defaults = dict(
        id=1,
        budget_max=500_000,
        min_beds=2,
        min_baths=1,
        min_sqft=1000,
        property_type="house",
        must_haves='["good school district", "3 bedrooms"]',
        nice_to_haves='["pool", "garage"]',
    )
    defaults.update(overrides)
    req = MagicMock()
    for k, v in defaults.items():
        setattr(req, k, v)
    req.must_haves_list = json.loads(defaults["must_haves"])
    req.nice_to_haves_list = json.loads(defaults["nice_to_haves"])
    return req


def _make_db_mock() -> MagicMock:
    """Create a mock DB session with add/commit/refresh stubs."""
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()
    return db


# ── Quantitative checks ───────────────────────────────────────────────────


class TestCheckNumeric:
    """Tests for the generic _check_numeric function."""

    def test_within_budget(self):
        result = _check_numeric(
            _make_listing(price=400_000), _make_requirement(budget_max=500_000),
            "budget_max", "price", "budget", "lte",
        )
        assert result["pass"] is True

    def test_over_budget(self):
        result = _check_numeric(
            _make_listing(price=600_000), _make_requirement(budget_max=500_000),
            "budget_max", "price", "budget", "lte",
        )
        assert result["pass"] is False

    def test_no_constraint(self):
        result = _check_numeric(
            _make_listing(price=999_999), _make_requirement(budget_max=None),
            "budget_max", "price", "budget", "lte",
        )
        assert result["pass"] is True

    def test_no_listing_data(self):
        result = _check_numeric(
            _make_listing(price=None), _make_requirement(budget_max=500_000),
            "budget_max", "price", "budget", "lte",
        )
        assert result["pass"] is False

    def test_gte_pass(self):
        result = _check_numeric(
            _make_listing(bedrooms=3), _make_requirement(min_beds=2),
            "min_beds", "bedrooms", "beds", "gte",
        )
        assert result["pass"] is True

    def test_gte_fail(self):
        result = _check_numeric(
            _make_listing(bedrooms=1), _make_requirement(min_beds=3),
            "min_beds", "bedrooms", "beds", "gte",
        )
        assert result["pass"] is False


class TestCheckPropertyType:
    def test_matching_type(self):
        assert _check_property_type(
            _make_listing(property_type="house"), _make_requirement(property_type="house"),
        )["pass"] is True

    def test_non_matching_type(self):
        assert _check_property_type(
            _make_listing(property_type="condo"), _make_requirement(property_type="house"),
        )["pass"] is False

    def test_case_insensitive(self):
        assert _check_property_type(
            _make_listing(property_type="House"), _make_requirement(property_type="house"),
        )["pass"] is True

    def test_no_constraint(self):
        assert _check_property_type(
            _make_listing(property_type="condo"), _make_requirement(property_type=""),
        )["pass"] is True


class TestRunQuantitativeChecks:
    def test_returns_all_check_keys(self):
        checks = _run_quantitative_checks(_make_listing(), _make_requirement())
        assert set(checks.keys()) == {"budget", "bedrooms", "bathrooms", "sqft", "property_type"}

    def test_all_pass_for_matching_listing(self):
        checks = _run_quantitative_checks(_make_listing(), _make_requirement())
        assert all(c["pass"] for c in checks.values())


# ── Full async rank_results ────────────────────────────────────────────────


class TestRankResults:
    @pytest.mark.asyncio
    async def test_empty_listings(self):
        result = await rank_results(
            _make_db_mock(), pipeline_run_id=1,
            requirement=_make_requirement(), listings=[], llm=MagicMock(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_with_llm_result(self):
        """rank_results should persist RankedResult objects and return them sorted."""
        listings = [
            _make_listing(id=1, price=400_000, bedrooms=3),
            _make_listing(id=2, price=600_000, bedrooms=2),
        ]
        req = _make_requirement(
            must_haves='["good school district"]',
            nice_to_haves='["pool"]',
        )

        llm_response = json.dumps({
            "listings": {
                "1": {
                    "must_have_checks": {
                        "good school district": {"pass": True, "reason": "Near top schools"},
                    },
                    "nice_to_have_scores": {
                        "pool": {"score": 0.8, "reason": "Community pool nearby"},
                    },
                },
                "2": {
                    "must_have_checks": {
                        "good school district": {"pass": False, "reason": "No schools nearby"},
                    },
                    "nice_to_have_scores": {
                        "pool": {"score": 0.2, "reason": "No pool"},
                    },
                },
            }
        })

        llm = MagicMock()
        llm.complete = AsyncMock(return_value=llm_response)
        db = _make_db_mock()

        results = await rank_results(
            db, pipeline_run_id=1, requirement=req, listings=listings, llm=llm,
        )

        assert len(results) == 2
        assert db.add.call_count == 2
        db.commit.assert_called_once()

        # Listing 1 should rank higher (within budget, passes must-have)
        assert results[0].listing_id == 1
        assert results[0].must_have_pass is True
        assert results[0].rank_position == 1

    @pytest.mark.asyncio
    async def test_llm_failure_graceful_fallback(self):
        """When LLM fails, semantic must-haves default to pass."""
        listings = [_make_listing(id=1)]
        req = _make_requirement(
            must_haves='["good school district"]',
            nice_to_haves='["pool"]',
        )

        llm = MagicMock()
        llm.complete = AsyncMock(side_effect=Exception("LLM down"))

        results = await rank_results(
            _make_db_mock(), pipeline_run_id=1, requirement=req, listings=listings, llm=llm,
        )

        assert len(results) == 1
        # Semantic must-have defaults to pass on LLM failure
        assert results[0].must_have_pass is True

    @pytest.mark.asyncio
    async def test_no_semantic_must_haves(self):
        """When all must-haves are quantitative, LLM is only called for nice-to-haves."""
        listings = [_make_listing(id=1)]
        req = _make_requirement(
            must_haves='["3 bedrooms"]',  # quantitative keyword
            nice_to_haves='[]',
        )

        llm = MagicMock()
        llm.complete = AsyncMock()

        results = await rank_results(
            _make_db_mock(), pipeline_run_id=1, requirement=req, listings=listings, llm=llm,
        )

        assert len(results) == 1
        # LLM should not have been called (no semantic must-haves, no nice-to-haves)
        llm.complete.assert_not_called()
