"""Rejection pattern learning: analyze past rejections to adjust ranking weights."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models.pipeline_run import PipelineRun
from app.models.rejection import RejectionReason

logger = logging.getLogger(__name__)

# Mapping from rejection reason keys to weight adjustment keys
_REASON_TO_BOOST_KEY: dict[str, str] = {
    "location_mismatch": "location_weight_boost",
    "overpriced": "price_weight_boost",
    "lot_too_small": "lot_size_weight_boost",
    "layout_inefficient": "layout_weight_boost",
    "basement_issue": "basement_weight_boost",
}

# Maximum boost multiplier (cap)
_MAX_BOOST = 2.0

# Boost scaling factor: boost = 1.0 + (reason_count / total) * _BOOST_SCALE
_BOOST_SCALE = 0.5


def _neutral_adjustments() -> dict[str, float]:
    """Return default (no-change) weight adjustments."""
    return {
        "location_weight_boost": 1.0,
        "price_weight_boost": 1.0,
        "lot_size_weight_boost": 1.0,
        "layout_weight_boost": 1.0,
        "basement_weight_boost": 1.0,
    }


def analyze_rejection_patterns(db: Session, transcript_id: int) -> dict[str, Any]:
    """Analyze all rejection reasons across pipeline runs for the same transcript.

    Returns weight adjustment factors based on rejection frequency.
    """
    # Find all pipeline runs for this transcript
    pipeline_run_ids = (
        db.query(PipelineRun.id)
        .filter(PipelineRun.transcript_id == transcript_id)
        .all()
    )
    run_ids = [r[0] for r in pipeline_run_ids]

    if not run_ids:
        return {
            "adjustments": _neutral_adjustments(),
            "rejection_summary": {},
            "total_rejections": 0,
            "top_reason": None,
        }

    # Query all rejection reasons for those pipeline runs
    rejections = (
        db.query(RejectionReason)
        .filter(RejectionReason.pipeline_run_id.in_(run_ids))
        .all()
    )

    total_rejections = len(rejections)
    if total_rejections == 0:
        return {
            "adjustments": _neutral_adjustments(),
            "rejection_summary": {},
            "total_rejections": 0,
            "top_reason": None,
        }

    # Count frequency of each rejection reason
    reason_counts: Counter[str] = Counter(r.reason for r in rejections)
    rejection_summary = dict(reason_counts)

    # Compute weight adjustments
    adjustments = _neutral_adjustments()
    for reason, count in reason_counts.items():
        boost_key = _REASON_TO_BOOST_KEY.get(reason)
        if boost_key:
            boost = 1.0 + (count / total_rejections) * _BOOST_SCALE
            adjustments[boost_key] = min(boost, _MAX_BOOST)

    # Find the most common rejection reason
    top_reason = reason_counts.most_common(1)[0][0]

    logger.info(
        "Rejection pattern analysis for transcript_id=%d: %d rejections, top=%s, adjustments=%s",
        transcript_id,
        total_rejections,
        top_reason,
        adjustments,
    )

    return {
        "adjustments": adjustments,
        "rejection_summary": rejection_summary,
        "total_rejections": total_rejections,
        "top_reason": top_reason,
    }
