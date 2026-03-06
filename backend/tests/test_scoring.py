"""Unit tests for the weighted scoring system in ranking_service._compute_scores."""

from __future__ import annotations

import json
import os
import sys

import pytest

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ranking_service import (  # noqa: E402
    MUST_HAVE_WEIGHT,
    NICE_TO_HAVE_WEIGHT,
    _compute_scores,
    _STRICT_PENALTY,
)


# ---------------------------------------------------------------------------
# Helpers – lightweight fakes that satisfy _compute_scores' interface
# ---------------------------------------------------------------------------


class _FakeListing:
    """Minimal stand-in for a Listing ORM object."""

    def __init__(self, listing_id: int = 1):
        self.id = listing_id


def _make_quant_checks(results: list[tuple[str, bool, str]]) -> dict[str, dict]:
    """Build quantitative checks dict from ``[(name, pass, reason), ...]``."""
    return {name: {"pass": passed, "reason": reason} for name, passed, reason in results}


def _make_llm_result(
    listing_id: int,
    must_have_checks: dict | None = None,
    nice_to_have_scores: dict | None = None,
) -> dict | None:
    if must_have_checks is None and nice_to_have_scores is None:
        return None
    inner: dict = {}
    if must_have_checks is not None:
        inner["must_have_checks"] = must_have_checks
    if nice_to_have_scores is not None:
        inner["nice_to_have_scores"] = nice_to_have_scores
    return {str(listing_id): inner}


# ---------------------------------------------------------------------------
# Test weight constants
# ---------------------------------------------------------------------------


class TestWeightConstants:
    def test_must_have_weight(self):
        assert MUST_HAVE_WEIGHT == 10

    def test_nice_to_have_weight(self):
        assert NICE_TO_HAVE_WEIGHT == 7


# ---------------------------------------------------------------------------
# All must-haves passing
# ---------------------------------------------------------------------------


class TestAllMustHavesPass:
    """Scenarios where every must-have check passes."""

    def test_strict_mode_all_pass(self):
        listing = _FakeListing(1)
        quant = _make_quant_checks([
            ("budget", True, "Under budget"),
            ("bedrooms", True, "3 beds >= 3 required"),
        ])
        result = _compute_scores(listing, quant, [], [], None, scoring_mode="strict")

        assert result["must_have_pass"] is True
        # nice-to-have defaults to 1.0 when there are none
        expected = (1.0 * MUST_HAVE_WEIGHT + 1.0 * NICE_TO_HAVE_WEIGHT) / (
            MUST_HAVE_WEIGHT + NICE_TO_HAVE_WEIGHT
        )
        assert result["overall_score"] == pytest.approx(expected, abs=1e-3)
        assert result["score_breakdown"]["scoring_mode"] == "strict"
        assert result["score_breakdown"]["must_have_satisfaction"] == pytest.approx(1.0)
        assert result["score_breakdown"]["nice_to_have_satisfaction"] == pytest.approx(1.0)

    def test_flexible_mode_all_pass(self):
        listing = _FakeListing(2)
        quant = _make_quant_checks([("budget", True, "ok")])
        result = _compute_scores(listing, quant, [], [], None, scoring_mode="flexible")

        assert result["must_have_pass"] is True
        expected = (1.0 * MUST_HAVE_WEIGHT + 1.0 * NICE_TO_HAVE_WEIGHT) / (
            MUST_HAVE_WEIGHT + NICE_TO_HAVE_WEIGHT
        )
        assert result["overall_score"] == pytest.approx(expected, abs=1e-3)
        assert result["score_breakdown"]["scoring_mode"] == "flexible"

    def test_all_pass_with_nice_to_haves(self):
        listing = _FakeListing(3)
        quant = _make_quant_checks([("budget", True, "ok")])
        llm = _make_llm_result(
            3,
            nice_to_have_scores={
                "pool": {"score": 0.8, "reason": "has pool"},
                "garage": {"score": 0.6, "reason": "2 car garage"},
            },
        )
        result = _compute_scores(
            listing, quant, [], ["pool", "garage"], llm, scoring_mode="strict"
        )

        assert result["must_have_pass"] is True
        nth_avg = (0.8 + 0.6) / 2
        expected = (1.0 * MUST_HAVE_WEIGHT + nth_avg * NICE_TO_HAVE_WEIGHT) / (
            MUST_HAVE_WEIGHT + NICE_TO_HAVE_WEIGHT
        )
        assert result["overall_score"] == pytest.approx(expected, abs=1e-3)
        assert result["score_breakdown"]["nice_to_have_satisfaction"] == pytest.approx(
            nth_avg, abs=1e-3
        )


# ---------------------------------------------------------------------------
# Some must-haves failing
# ---------------------------------------------------------------------------


class TestSomeMustHavesFail:
    """Scenarios where some (but not all) must-haves fail."""

    def _base_quant(self) -> dict:
        return _make_quant_checks([
            ("budget", True, "Under budget"),
            ("bedrooms", False, "2 beds < 3 required"),
            ("bathrooms", True, "2 baths >= 2 required"),
        ])

    def test_strict_mode_some_fail(self):
        listing = _FakeListing(10)
        quant = self._base_quant()
        result = _compute_scores(listing, quant, [], [], None, scoring_mode="strict")

        assert result["must_have_pass"] is False
        mh_sat = 2.0 / 3.0
        nth_sat = 1.0  # no nice-to-haves → default 1.0
        raw = (mh_sat * MUST_HAVE_WEIGHT + nth_sat * NICE_TO_HAVE_WEIGHT) / (
            MUST_HAVE_WEIGHT + NICE_TO_HAVE_WEIGHT
        )
        expected = raw * _STRICT_PENALTY
        assert result["overall_score"] == pytest.approx(expected, abs=1e-3)

    def test_flexible_mode_some_fail(self):
        listing = _FakeListing(11)
        quant = self._base_quant()
        result = _compute_scores(listing, quant, [], [], None, scoring_mode="flexible")

        assert result["must_have_pass"] is False
        mh_sat = 2.0 / 3.0
        nth_sat = 1.0
        expected = (mh_sat * MUST_HAVE_WEIGHT + nth_sat * NICE_TO_HAVE_WEIGHT) / (
            MUST_HAVE_WEIGHT + NICE_TO_HAVE_WEIGHT
        )
        # No penalty in flexible mode
        assert result["overall_score"] == pytest.approx(expected, abs=1e-3)

    def test_strict_score_lower_than_flexible(self):
        listing = _FakeListing(12)
        quant = self._base_quant()
        strict = _compute_scores(listing, quant, [], [], None, scoring_mode="strict")
        flexible = _compute_scores(listing, quant, [], [], None, scoring_mode="flexible")

        assert strict["overall_score"] < flexible["overall_score"]


# ---------------------------------------------------------------------------
# No must-haves passing (all fail)
# ---------------------------------------------------------------------------


class TestNoMustHavesPass:
    """Scenarios where every must-have fails."""

    def _all_fail_quant(self) -> dict:
        return _make_quant_checks([
            ("budget", False, "Over budget"),
            ("bedrooms", False, "Too few beds"),
            ("bathrooms", False, "Too few baths"),
        ])

    def test_strict_mode_none_pass(self):
        listing = _FakeListing(20)
        quant = self._all_fail_quant()
        result = _compute_scores(listing, quant, [], [], None, scoring_mode="strict")

        assert result["must_have_pass"] is False
        assert result["score_breakdown"]["must_have_satisfaction"] == pytest.approx(0.0)
        # With must_have_satisfaction=0, nice_to_have_satisfaction defaults to 1.0
        raw = (0.0 * MUST_HAVE_WEIGHT + 1.0 * NICE_TO_HAVE_WEIGHT) / (
            MUST_HAVE_WEIGHT + NICE_TO_HAVE_WEIGHT
        )
        expected = raw * _STRICT_PENALTY
        assert result["overall_score"] == pytest.approx(expected, abs=1e-3)

    def test_flexible_mode_none_pass(self):
        listing = _FakeListing(21)
        quant = self._all_fail_quant()
        result = _compute_scores(listing, quant, [], [], None, scoring_mode="flexible")

        assert result["must_have_pass"] is False
        raw = (0.0 * MUST_HAVE_WEIGHT + 1.0 * NICE_TO_HAVE_WEIGHT) / (
            MUST_HAVE_WEIGHT + NICE_TO_HAVE_WEIGHT
        )
        # No penalty in flexible mode
        assert result["overall_score"] == pytest.approx(raw, abs=1e-3)

    def test_all_fail_with_low_nice_to_haves(self):
        listing = _FakeListing(22)
        quant = self._all_fail_quant()
        llm = _make_llm_result(
            22,
            nice_to_have_scores={
                "pool": {"score": 0.1, "reason": "no pool"},
                "view": {"score": 0.2, "reason": "no view"},
            },
        )
        result = _compute_scores(
            listing, quant, [], ["pool", "view"], llm, scoring_mode="strict"
        )

        nth_avg = (0.1 + 0.2) / 2
        raw = (0.0 * MUST_HAVE_WEIGHT + nth_avg * NICE_TO_HAVE_WEIGHT) / (
            MUST_HAVE_WEIGHT + NICE_TO_HAVE_WEIGHT
        )
        expected = raw * _STRICT_PENALTY
        assert result["overall_score"] == pytest.approx(expected, abs=1e-3)
        assert result["score_breakdown"]["nice_to_have_satisfaction"] == pytest.approx(
            nth_avg, abs=1e-3
        )


# ---------------------------------------------------------------------------
# Score breakdown JSON structure
# ---------------------------------------------------------------------------


class TestScoreBreakdownStructure:
    """Verify the breakdown dict has all required keys."""

    def test_breakdown_keys_strict(self):
        listing = _FakeListing(30)
        quant = _make_quant_checks([("budget", True, "ok")])
        result = _compute_scores(listing, quant, [], [], None, scoring_mode="strict")

        bd = result["score_breakdown"]
        assert "must_have_checks" in bd
        assert "nice_to_have_details" in bd
        assert "must_have_rate" in bd
        assert "must_have_satisfaction" in bd
        assert "nice_to_have_satisfaction" in bd
        assert "scoring_mode" in bd
        assert "weights" in bd
        assert bd["weights"] == {
            "must_have": MUST_HAVE_WEIGHT,
            "nice_to_have": NICE_TO_HAVE_WEIGHT,
        }
        assert bd["scoring_mode"] == "strict"

    def test_breakdown_keys_flexible(self):
        listing = _FakeListing(31)
        quant = _make_quant_checks([("budget", False, "over")])
        result = _compute_scores(listing, quant, [], [], None, scoring_mode="flexible")

        bd = result["score_breakdown"]
        assert bd["scoring_mode"] == "flexible"
        assert bd["weights"]["must_have"] == MUST_HAVE_WEIGHT
        assert bd["weights"]["nice_to_have"] == NICE_TO_HAVE_WEIGHT

    def test_breakdown_is_json_serializable(self):
        listing = _FakeListing(32)
        quant = _make_quant_checks([("budget", True, "ok"), ("beds", False, "nope")])
        result = _compute_scores(listing, quant, [], [], None, scoring_mode="strict")
        # Should not raise
        json.dumps(result["score_breakdown"])


# ---------------------------------------------------------------------------
# Default scoring_mode is strict
# ---------------------------------------------------------------------------


class TestDefaultScoringMode:
    def test_defaults_to_strict(self):
        listing = _FakeListing(40)
        quant = _make_quant_checks([("budget", False, "over")])
        result = _compute_scores(listing, quant, [], [], None)
        assert result["score_breakdown"]["scoring_mode"] == "strict"
        # Should have penalty applied
        no_penalty = _compute_scores(
            listing, quant, [], [], None, scoring_mode="flexible"
        )
        assert result["overall_score"] < no_penalty["overall_score"]


# ---------------------------------------------------------------------------
# Semantic must-haves via LLM
# ---------------------------------------------------------------------------


class TestSemanticMustHaves:
    def test_semantic_must_have_fail_strict(self):
        listing = _FakeListing(50)
        quant = _make_quant_checks([("budget", True, "ok")])
        llm = _make_llm_result(
            50,
            must_have_checks={
                "near subway": {"pass": False, "reason": "no subway nearby"},
            },
        )
        result = _compute_scores(
            listing, quant, ["near subway"], [], llm, scoring_mode="strict"
        )
        assert result["must_have_pass"] is False
        # Penalty applied
        assert result["score_breakdown"]["must_have_satisfaction"] == pytest.approx(0.5)

    def test_semantic_must_have_fail_flexible(self):
        listing = _FakeListing(51)
        quant = _make_quant_checks([("budget", True, "ok")])
        llm = _make_llm_result(
            51,
            must_have_checks={
                "near subway": {"pass": False, "reason": "no subway nearby"},
            },
        )
        strict = _compute_scores(
            listing, quant, ["near subway"], [], llm, scoring_mode="strict"
        )
        flexible = _compute_scores(
            listing, quant, ["near subway"], [], llm, scoring_mode="flexible"
        )
        assert flexible["overall_score"] > strict["overall_score"]
