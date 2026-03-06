"""Tests for rejection pattern learning and dynamic weight adjustments."""

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
from app.services.rejection_learning_service import (  # noqa: E402
    _BOOST_SCALE,
    _MAX_BOOST,
    _neutral_adjustments,
    analyze_rejection_patterns,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeListing:
    """Minimal stand-in for a Listing ORM object."""

    def __init__(self, listing_id: int = 1):
        self.id = listing_id


def _make_quant_checks(results: list[tuple[str, bool, str]]) -> dict[str, dict]:
    return {name: {"pass": passed, "reason": reason} for name, passed, reason in results}


class _FakeRejection:
    """Minimal stand-in for a RejectionReason record."""

    def __init__(self, reason: str, pipeline_run_id: int = 1):
        self.reason = reason
        self.pipeline_run_id = pipeline_run_id


class _FakePipelineRun:
    def __init__(self, run_id: int, transcript_id: int):
        self.id = run_id
        self.transcript_id = transcript_id


class _FakeQuery:
    """Very small query-like object for test faking."""

    def __init__(self, results):
        self._results = results

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._results


class _FakeDB:
    """Fake DB session that returns pre-configured results."""

    def __init__(
        self,
        pipeline_runs: list[tuple[int]] | None = None,
        rejections: list[_FakeRejection] | None = None,
    ):
        self._pipeline_runs = pipeline_runs or []
        self._rejections = rejections or []
        self._call_count = 0

    def query(self, model):
        self._call_count += 1
        # First call is for PipelineRun.id, second for RejectionReason
        if self._call_count == 1:
            return _FakeQuery(self._pipeline_runs)
        return _FakeQuery(self._rejections)


# ---------------------------------------------------------------------------
# Test analyze_rejection_patterns: no rejections
# ---------------------------------------------------------------------------


class TestNoRejections:
    def test_no_pipeline_runs(self):
        db = _FakeDB(pipeline_runs=[], rejections=[])
        result = analyze_rejection_patterns(db, transcript_id=1)

        assert result["total_rejections"] == 0
        assert result["top_reason"] is None
        assert result["rejection_summary"] == {}
        assert result["adjustments"] == _neutral_adjustments()

    def test_pipeline_runs_but_no_rejections(self):
        db = _FakeDB(pipeline_runs=[(1,), (2,)], rejections=[])
        result = analyze_rejection_patterns(db, transcript_id=1)

        assert result["total_rejections"] == 0
        assert result["top_reason"] is None
        assert result["adjustments"] == _neutral_adjustments()


# ---------------------------------------------------------------------------
# Test analyze_rejection_patterns: single reason type
# ---------------------------------------------------------------------------


class TestSingleReasonType:
    def test_all_location_mismatch(self):
        rejections = [
            _FakeRejection("location_mismatch"),
            _FakeRejection("location_mismatch"),
            _FakeRejection("location_mismatch"),
        ]
        db = _FakeDB(pipeline_runs=[(1,)], rejections=rejections)
        result = analyze_rejection_patterns(db, transcript_id=1)

        assert result["total_rejections"] == 3
        assert result["top_reason"] == "location_mismatch"
        assert result["rejection_summary"]["location_mismatch"] == 3

        # boost = 1.0 + (3/3) * 0.5 = 1.5
        assert result["adjustments"]["location_weight_boost"] == pytest.approx(1.5)
        # Other adjustments should remain 1.0
        assert result["adjustments"]["price_weight_boost"] == pytest.approx(1.0)
        assert result["adjustments"]["lot_size_weight_boost"] == pytest.approx(1.0)
        assert result["adjustments"]["layout_weight_boost"] == pytest.approx(1.0)
        assert result["adjustments"]["basement_weight_boost"] == pytest.approx(1.0)

    def test_all_overpriced(self):
        rejections = [_FakeRejection("overpriced")] * 5
        db = _FakeDB(pipeline_runs=[(1,)], rejections=rejections)
        result = analyze_rejection_patterns(db, transcript_id=1)

        assert result["total_rejections"] == 5
        assert result["top_reason"] == "overpriced"
        # boost = 1.0 + (5/5) * 0.5 = 1.5
        assert result["adjustments"]["price_weight_boost"] == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# Test analyze_rejection_patterns: mixed rejections
# ---------------------------------------------------------------------------


class TestMixedRejections:
    def test_proportional_boosts(self):
        rejections = [
            _FakeRejection("location_mismatch"),
            _FakeRejection("location_mismatch"),
            _FakeRejection("overpriced"),
            _FakeRejection("lot_too_small"),
        ]
        db = _FakeDB(pipeline_runs=[(1,)], rejections=rejections)
        result = analyze_rejection_patterns(db, transcript_id=1)

        total = 4
        assert result["total_rejections"] == total
        assert result["top_reason"] == "location_mismatch"

        # location: 1.0 + (2/4) * 0.5 = 1.25
        assert result["adjustments"]["location_weight_boost"] == pytest.approx(1.25)
        # price: 1.0 + (1/4) * 0.5 = 1.125
        assert result["adjustments"]["price_weight_boost"] == pytest.approx(1.125)
        # lot_size: 1.0 + (1/4) * 0.5 = 1.125
        assert result["adjustments"]["lot_size_weight_boost"] == pytest.approx(1.125)
        # layout and basement: 1.0 (no rejections)
        assert result["adjustments"]["layout_weight_boost"] == pytest.approx(1.0)
        assert result["adjustments"]["basement_weight_boost"] == pytest.approx(1.0)

    def test_informational_reasons_ignored(self):
        """not_enough_light and other don't map to boost keys."""
        rejections = [
            _FakeRejection("not_enough_light"),
            _FakeRejection("other"),
            _FakeRejection("location_mismatch"),
        ]
        db = _FakeDB(pipeline_runs=[(1,)], rejections=rejections)
        result = analyze_rejection_patterns(db, transcript_id=1)

        assert result["total_rejections"] == 3
        # location: 1.0 + (1/3) * 0.5 ≈ 1.1667
        assert result["adjustments"]["location_weight_boost"] == pytest.approx(
            1.0 + (1 / 3) * 0.5, abs=1e-4
        )
        # Others remain 1.0
        assert result["adjustments"]["price_weight_boost"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test weight cap at 2.0
# ---------------------------------------------------------------------------


class TestWeightCap:
    def test_cap_at_max_boost(self):
        """Even with extreme counts, boost should not exceed _MAX_BOOST."""
        # With _BOOST_SCALE=0.5, the max possible is 1.0 + 1.0*0.5 = 1.5,
        # which is below 2.0.  But let's verify cap logic works with a
        # hypothetical scenario by testing the formula boundary.
        rejections = [_FakeRejection("overpriced")] * 100
        db = _FakeDB(pipeline_runs=[(1,)], rejections=rejections)
        result = analyze_rejection_patterns(db, transcript_id=1)

        # 1.0 + (100/100) * 0.5 = 1.5 — under the cap
        assert result["adjustments"]["price_weight_boost"] == pytest.approx(1.5)
        assert result["adjustments"]["price_weight_boost"] <= _MAX_BOOST

    def test_boost_formula(self):
        """Verify boost = min(1.0 + (count/total) * BOOST_SCALE, MAX_BOOST)."""
        rejections = [
            _FakeRejection("overpriced"),
            _FakeRejection("overpriced"),
            _FakeRejection("location_mismatch"),
        ]
        db = _FakeDB(pipeline_runs=[(1,)], rejections=rejections)
        result = analyze_rejection_patterns(db, transcript_id=1)

        expected_price = min(1.0 + (2 / 3) * _BOOST_SCALE, _MAX_BOOST)
        expected_location = min(1.0 + (1 / 3) * _BOOST_SCALE, _MAX_BOOST)
        assert result["adjustments"]["price_weight_boost"] == pytest.approx(
            expected_price, abs=1e-4
        )
        assert result["adjustments"]["location_weight_boost"] == pytest.approx(
            expected_location, abs=1e-4
        )


# ---------------------------------------------------------------------------
# Test _compute_scores with weight_adjustments
# ---------------------------------------------------------------------------


class TestComputeScoresWithAdjustments:
    def test_no_adjustments_same_as_default(self):
        """Passing None or empty adjustments should produce identical results."""
        listing = _FakeListing(1)
        quant = _make_quant_checks([
            ("budget", True, "Under budget"),
            ("bedrooms", True, "3 beds >= 3 required"),
        ])
        result_none = _compute_scores(listing, quant, [], [], None, weight_adjustments=None)
        result_empty = _compute_scores(listing, quant, [], [], None, weight_adjustments={})

        assert result_none["overall_score"] == result_empty["overall_score"]
        assert result_none["must_have_pass"] == result_empty["must_have_pass"]

    def test_adjustments_included_in_breakdown(self):
        """weight_adjustments should appear in score_breakdown when provided."""
        listing = _FakeListing(1)
        quant = _make_quant_checks([("budget", True, "ok")])
        adj = {"price_weight_boost": 1.25}
        result = _compute_scores(listing, quant, [], [], None, weight_adjustments=adj)

        assert "weight_adjustments" in result["score_breakdown"]
        assert result["score_breakdown"]["weight_adjustments"] == adj

    def test_no_adjustments_key_when_none(self):
        """weight_adjustments key should not appear when no adjustments given."""
        listing = _FakeListing(1)
        quant = _make_quant_checks([("budget", True, "ok")])
        result = _compute_scores(listing, quant, [], [], None, weight_adjustments=None)

        assert "weight_adjustments" not in result["score_breakdown"]

    def test_budget_fail_with_price_boost_lowers_score(self):
        """A failed budget check with boosted price weight should lower the overall score."""
        listing = _FakeListing(1)
        quant = _make_quant_checks([
            ("budget", False, "Over budget"),
            ("bedrooms", True, "3 beds >= 3 required"),
        ])

        result_no_adj = _compute_scores(
            listing, quant, [], [], None, scoring_mode="flexible"
        )
        result_with_adj = _compute_scores(
            listing, quant, [], [], None, scoring_mode="flexible",
            weight_adjustments={"price_weight_boost": 1.5},
        )

        # With a boost on the failing budget check, the weighted must-have
        # satisfaction should be lower, leading to a lower overall score.
        assert result_with_adj["overall_score"] < result_no_adj["overall_score"]

    def test_budget_pass_with_price_boost_raises_score(self):
        """A passed budget check with boosted price weight should raise the score
        when there's also a failing check."""
        listing = _FakeListing(1)
        quant = _make_quant_checks([
            ("budget", True, "Under budget"),
            ("bedrooms", False, "2 beds < 3 required"),
        ])

        result_no_adj = _compute_scores(
            listing, quant, [], [], None, scoring_mode="flexible"
        )
        result_with_adj = _compute_scores(
            listing, quant, [], [], None, scoring_mode="flexible",
            weight_adjustments={"price_weight_boost": 1.5},
        )

        # Budget passes and is boosted, bedrooms fail with default weight.
        # The weighted satisfaction should be higher than the unweighted one.
        assert result_with_adj["overall_score"] > result_no_adj["overall_score"]

    def test_breakdown_json_serializable_with_adjustments(self):
        listing = _FakeListing(1)
        quant = _make_quant_checks([("budget", True, "ok")])
        adj = {"price_weight_boost": 1.3, "location_weight_boost": 1.1}
        result = _compute_scores(listing, quant, [], [], None, weight_adjustments=adj)

        # Should not raise
        json.dumps(result["score_breakdown"])


# ---------------------------------------------------------------------------
# Integration: rejection patterns flow through to ranking scores
# ---------------------------------------------------------------------------


class TestIntegrationFlow:
    """Verify that rejection learning adjustments affect scoring end-to-end."""

    def test_adjustments_change_relative_ranking(self):
        """Two listings: one fails budget, other fails bedrooms.
        With a price_weight_boost, the budget-failing listing should rank lower
        relative to the baseline."""
        listing_a = _FakeListing(1)  # fails budget
        listing_b = _FakeListing(2)  # fails bedrooms

        quant_a = _make_quant_checks([
            ("budget", False, "Over budget"),
            ("bedrooms", True, "3 beds"),
        ])
        quant_b = _make_quant_checks([
            ("budget", True, "Under budget"),
            ("bedrooms", False, "2 beds"),
        ])

        # Without adjustments (flexible mode for simpler comparison)
        score_a_base = _compute_scores(
            listing_a, quant_a, [], [], None, scoring_mode="flexible"
        )["overall_score"]
        score_b_base = _compute_scores(
            listing_b, quant_b, [], [], None, scoring_mode="flexible"
        )["overall_score"]

        # Baseline: both have same must-have satisfaction (1/2)
        assert score_a_base == pytest.approx(score_b_base)

        # With price boost: budget failure is more costly
        adj = {"price_weight_boost": 1.5}
        score_a_adj = _compute_scores(
            listing_a, quant_a, [], [], None, scoring_mode="flexible",
            weight_adjustments=adj,
        )["overall_score"]
        score_b_adj = _compute_scores(
            listing_b, quant_b, [], [], None, scoring_mode="flexible",
            weight_adjustments=adj,
        )["overall_score"]

        # listing_a (budget fail + boosted price) should score lower than listing_b
        assert score_a_adj < score_b_adj
