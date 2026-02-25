"""Ranking engine: two-phase scoring (algorithmic + LLM semantic).

Phase 2 (LLM semantic evaluation) is kicked off as an ``asyncio`` task
before Phase 1 (quantitative checks) runs inline, so the cheap CPU work
overlaps with the slow LLM network call.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.llm.base import LLMProvider
from app.llm.prompts.ranking import RANKING_SYSTEM_PROMPT, build_ranking_user_prompt
from app.models.listing import Listing
from app.models.ranking import RankedResult
from app.models.requirement import ExtractedRequirement

logger = logging.getLogger(__name__)

# ── Quantitative must-have checks (no LLM needed) ────────────────────────

# Each entry: (check_name, constraint_attr, listing_attr, label, comparison)
# comparison: "gte" for listing_value >= constraint, "lte" for <=
_NUMERIC_CHECKS: list[tuple[str, str, str, str, str]] = [
    ("budget",   "budget_max", "price",    "budget",   "lte"),
    ("bedrooms", "min_beds",   "bedrooms", "beds",     "gte"),
    ("bathrooms","min_baths",  "bathrooms","baths",    "gte"),
    ("sqft",     "min_sqft",   "sqft",     "sqft",     "gte"),
]


def _format_value(value: float | int, label: str) -> str:
    """Format a numeric value for human-readable check reasons."""
    if label == "budget":
        return f"${value:,.0f}"
    if label == "sqft":
        return f"{value:,}"
    return str(value)


def _check_numeric(
    listing: Listing, requirement: ExtractedRequirement,
    constraint_attr: str, listing_attr: str, label: str, comparison: str,
) -> dict:
    """Generic numeric check: compare a listing value against a requirement constraint."""
    constraint = getattr(requirement, constraint_attr)
    if not constraint:
        return {"pass": True, "reason": f"No {label} constraint"}
    listing_value = getattr(listing, listing_attr)
    if listing_value is None:
        return {"pass": False, "reason": f"Listing has no {label} data"}

    if comparison == "lte":
        passed = listing_value <= constraint
        op = "<=" if passed else ">"
    else:  # gte
        passed = listing_value >= constraint
        op = ">=" if passed else "<"

    lv = _format_value(listing_value, label)
    cv = _format_value(constraint, label)
    return {"pass": passed, "reason": f"{lv} {label} {op} {cv} required"}


def _check_property_type(listing: Listing, requirement: ExtractedRequirement) -> dict:
    if not requirement.property_type or requirement.property_type.strip() == "":
        return {"pass": True, "reason": "No property type constraint"}
    if listing.property_type is None:
        return {"pass": False, "reason": "Listing has no property type data"}
    passed = listing.property_type.lower().strip() == requirement.property_type.lower().strip()
    verb = "matches" if passed else "does not match"
    return {
        "pass": passed,
        "reason": f"Type '{listing.property_type}' {verb} required '{requirement.property_type}'",
    }


def _run_quantitative_checks(
    listing: Listing, requirement: ExtractedRequirement
) -> dict[str, dict]:
    """Run all algorithmic must-have checks for a single listing."""
    checks = {
        name: _check_numeric(listing, requirement, constraint_attr, listing_attr, label, cmp)
        for name, constraint_attr, listing_attr, label, cmp in _NUMERIC_CHECKS
    }
    checks["property_type"] = _check_property_type(listing, requirement)
    return checks


# ── Semantic must-have filtering ──────────────────────────────────────────

QUANTITATIVE_KEYWORDS = [
    "bedroom", "bed", "bath", "bathroom", "budget", "price",
    "sqft", "square feet", "square foot", "sq ft",
    "property type", "house", "condo", "townhouse",
]


def _is_quantitative_must_have(must_have: str) -> bool:
    """Heuristic: skip must-haves that overlap with quantitative checks."""
    lower = must_have.lower()
    return any(kw in lower for kw in QUANTITATIVE_KEYWORDS)


def _get_semantic_must_haves(requirement: ExtractedRequirement) -> list[str]:
    """Filter must_haves_list to items needing LLM evaluation."""
    return [mh for mh in requirement.must_haves_list if not _is_quantitative_must_have(mh)]


# ── LLM semantic evaluation ──────────────────────────────────────────────


_LISTING_FIELDS = (
    "id", "address", "price", "bedrooms", "bathrooms", "sqft",
    "property_type", "description", "neighborhood", "year_built",
    "days_on_market",
)


def _listings_to_dicts(listings: list[Listing]) -> list[dict]:
    """Convert Listing ORM objects to dicts for prompt building."""
    return [
        {field: getattr(listing, field) for field in _LISTING_FIELDS}
        for listing in listings
    ]


def _parse_llm_response(raw_text: str) -> dict[str, Any]:
    """Parse JSON from LLM, stripping markdown fences if present."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


async def _evaluate_semantic(
    llm: LLMProvider,
    semantic_must_haves: list[str],
    nice_to_haves: list[str],
    listings: list[Listing],
) -> dict[str, Any] | None:
    """Call LLM to evaluate semantic must-haves and nice-to-haves.

    Returns dict keyed by listing ID (as string), or None on failure.
    """
    if not semantic_must_haves and not nice_to_haves:
        return None

    listing_dicts = _listings_to_dicts(listings)
    user_prompt = build_ranking_user_prompt(
        semantic_must_haves, nice_to_haves, listing_dicts
    )

    try:
        raw_response = await llm.complete(RANKING_SYSTEM_PROMPT, user_prompt)
    except Exception:
        logger.exception("LLM ranking API call failed")
        return None

    try:
        parsed = _parse_llm_response(raw_response)
    except (json.JSONDecodeError, ValueError):
        logger.error(
            "LLM ranking response was not valid JSON. First 500 chars: %s",
            raw_response[:500],
        )
        return None

    # The LLM may return {"listings": {...}} or just the inner dict directly
    result = parsed.get("listings", parsed) if isinstance(parsed, dict) else None
    if not isinstance(result, dict) or not result:
        logger.error(
            "LLM ranking response missing 'listings' key or empty. Keys: %s",
            list(parsed.keys()) if isinstance(parsed, dict) else type(parsed),
        )
        return None

    return result


# ── Score computation ─────────────────────────────────────────────────────


def _compute_scores(
    listing: Listing,
    quant_checks: dict[str, dict],
    semantic_must_haves: list[str],
    nice_to_haves: list[str],
    llm_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Combine quantitative and semantic results into final scores."""
    listing_llm = (llm_result or {}).get(str(listing.id), {})

    # ── Must-have evaluation ──
    all_must_have_checks: dict[str, dict] = dict(quant_checks)

    if listing_llm:
        semantic_checks = listing_llm.get("must_have_checks", {})
        for mh_text in semantic_must_haves:
            all_must_have_checks[mh_text] = semantic_checks.get(
                mh_text, {"pass": False, "reason": "Not evaluated by LLM"}
            )
    elif semantic_must_haves:
        # LLM failed — default semantic must-haves to pass (graceful fallback)
        for mh_text in semantic_must_haves:
            all_must_have_checks[mh_text] = {
                "pass": True,
                "reason": "LLM unavailable; defaulting to pass",
            }

    must_have_pass = all(c["pass"] for c in all_must_have_checks.values())
    total_mh = len(all_must_have_checks)
    passed_mh = sum(1 for c in all_must_have_checks.values() if c["pass"])
    must_have_rate = passed_mh / total_mh if total_mh > 0 else 1.0

    # ── Nice-to-have evaluation ──
    nice_to_have_details: dict[str, dict] = {}

    if listing_llm:
        nth_scores = listing_llm.get("nice_to_have_scores", {})
        for nth_text in nice_to_haves:
            nice_to_have_details[nth_text] = nth_scores.get(
                nth_text, {"score": 0.5, "reason": "Not evaluated"}
            )
    elif nice_to_haves:
        for nth_text in nice_to_haves:
            nice_to_have_details[nth_text] = {
                "score": 0.5,
                "reason": "LLM unavailable; default score",
            }

    if nice_to_have_details:
        nice_to_have_score = sum(
            d.get("score", 0.5) for d in nice_to_have_details.values()
        ) / len(nice_to_have_details)
    else:
        nice_to_have_score = 1.0

    # ── Overall score ──
    # 60% must-have pass rate + 40% nice-to-have score
    # Hard penalty if any must-have fails
    nth_weight = nice_to_have_score if must_have_pass else nice_to_have_score * 0.5
    overall_score = 0.6 * must_have_rate + 0.4 * nth_weight

    return {
        "overall_score": round(overall_score, 4),
        "must_have_pass": must_have_pass,
        "nice_to_have_score": round(nice_to_have_score, 4),
        "score_breakdown": {
            "must_have_checks": all_must_have_checks,
            "nice_to_have_details": nice_to_have_details,
            "must_have_rate": round(must_have_rate, 4),
            "weights": {"must_have": 0.6, "nice_to_have": 0.4},
        },
    }


# ── Public API ────────────────────────────────────────────────────────────


async def rank_results(
    db: Session,
    pipeline_run_id: int,
    requirement: ExtractedRequirement,
    listings: list[Listing],
    llm: LLMProvider,
) -> list[RankedResult]:
    """Score, rank, and persist RankedResult records.

    Returns list of RankedResult ORM objects sorted by score descending.

    Phase 2 (LLM semantic evaluation) is started as an ``asyncio.create_task``
    before Phase 1 (quantitative checks) runs inline, so the two overlap.
    """
    if not listings:
        return []

    semantic_must_haves = _get_semantic_must_haves(requirement)
    nice_to_haves = requirement.nice_to_haves_list

    logger.info(
        "Ranking %d listings: %d quantitative checks, %d semantic must-haves, %d nice-to-haves",
        len(listings),
        len(_NUMERIC_CHECKS) + 1,
        len(semantic_must_haves),
        len(nice_to_haves),
    )

    # Phase 1 (quantitative) starts inline; Phase 2 (LLM) starts concurrently.
    # The LLM network call dominates wall-clock time, so we kick it off first
    # and run the cheap quantitative checks while awaiting the response.
    llm_task = asyncio.create_task(
        _evaluate_semantic(llm, semantic_must_haves, nice_to_haves, listings)
    )

    quant_results = {
        listing.id: _run_quantitative_checks(listing, requirement)
        for listing in listings
    }

    llm_result = await llm_task

    # Phase 3: Compute final scores
    scored = [
        (
            listing,
            _compute_scores(
                listing, quant_results[listing.id],
                semantic_must_haves, nice_to_haves, llm_result,
            ),
        )
        for listing in listings
    ]

    # Sort: must_have_pass=True first, then overall_score descending
    scored.sort(
        key=lambda x: (x[1]["must_have_pass"], x[1]["overall_score"]),
        reverse=True,
    )

    # Persist to DB
    ranked_results: list[RankedResult] = []
    for position, (listing, scores) in enumerate(scored, start=1):
        ranked_result = RankedResult(
            pipeline_run_id=pipeline_run_id,
            listing_id=listing.id,
            requirement_id=requirement.id,
            overall_score=scores["overall_score"],
            must_have_pass=scores["must_have_pass"],
            nice_to_have_score=scores["nice_to_have_score"],
            rank_position=position,
            score_breakdown_json=json.dumps(scores["score_breakdown"]),
        )
        db.add(ranked_result)
        ranked_results.append(ranked_result)

    db.commit()
    for rr in ranked_results:
        db.refresh(rr)

    passed_count = sum(1 for r in ranked_results if r.must_have_pass)
    logger.info(
        "Ranked %d listings for pipeline_run_id=%d; %d passed all must-haves",
        len(ranked_results),
        pipeline_run_id,
        passed_count,
    )
    return ranked_results


def get_rankings_by_pipeline_run(
    db: Session, pipeline_run_id: int
) -> list[RankedResult]:
    """Retrieve persisted rankings ordered by rank_position."""
    return (
        db.query(RankedResult)
        .filter(RankedResult.pipeline_run_id == pipeline_run_id)
        .order_by(RankedResult.rank_position.asc())
        .all()
    )
