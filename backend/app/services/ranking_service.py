"""Ranking engine: two-phase scoring (algorithmic + LLM semantic)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from app.llm.prompts.ranking import RANKING_SYSTEM_PROMPT, build_ranking_user_prompt
from app.models.ranking import RankedResult

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.llm.base import LLMProvider
    from app.models.listing import Listing
    from app.models.requirement import ExtractedRequirement

logger = logging.getLogger(__name__)

# ── Quantitative must-have checks (no LLM needed) ────────────────────────


def _check_budget(listing: Listing, requirement: ExtractedRequirement) -> dict:
    if not requirement.budget_max or requirement.budget_max == 0:
        return {"pass": True, "reason": "No budget constraint specified"}
    if listing.price is None:
        return {"pass": False, "reason": "Listing has no price data"}
    passed = listing.price <= requirement.budget_max
    op = "<=" if passed else ">"
    return {
        "pass": passed,
        "reason": f"${listing.price:,.0f} {op} ${requirement.budget_max:,.0f} budget",
    }


def _check_bedrooms(listing: Listing, requirement: ExtractedRequirement) -> dict:
    if not requirement.min_beds or requirement.min_beds == 0:
        return {"pass": True, "reason": "No bedroom constraint"}
    if listing.bedrooms is None:
        return {"pass": False, "reason": "Listing has no bedroom data"}
    passed = listing.bedrooms >= requirement.min_beds
    op = ">=" if passed else "<"
    return {
        "pass": passed,
        "reason": f"{listing.bedrooms} beds {op} {requirement.min_beds} required",
    }


def _check_bathrooms(listing: Listing, requirement: ExtractedRequirement) -> dict:
    if not requirement.min_baths or requirement.min_baths == 0:
        return {"pass": True, "reason": "No bathroom constraint"}
    if listing.bathrooms is None:
        return {"pass": False, "reason": "Listing has no bathroom data"}
    passed = listing.bathrooms >= requirement.min_baths
    op = ">=" if passed else "<"
    return {
        "pass": passed,
        "reason": f"{listing.bathrooms} baths {op} {requirement.min_baths} required",
    }


def _check_sqft(listing: Listing, requirement: ExtractedRequirement) -> dict:
    if not requirement.min_sqft or requirement.min_sqft == 0:
        return {"pass": True, "reason": "No sqft constraint"}
    if listing.sqft is None:
        return {"pass": False, "reason": "Listing has no sqft data"}
    passed = listing.sqft >= requirement.min_sqft
    op = ">=" if passed else "<"
    return {
        "pass": passed,
        "reason": f"{listing.sqft:,} sqft {op} {requirement.min_sqft:,} required",
    }


def _check_property_type(listing: Listing, requirement: ExtractedRequirement) -> dict:
    if not requirement.property_type or requirement.property_type.strip() == "":
        return {"pass": True, "reason": "No property type constraint"}
    if listing.property_type is None:
        return {"pass": False, "reason": "Listing has no property type data"}
    passed = (
        listing.property_type.lower().strip()
        == requirement.property_type.lower().strip()
    )
    verb = "matches" if passed else "does not match"
    return {
        "pass": passed,
        "reason": f"Type '{listing.property_type}' {verb} required '{requirement.property_type}'",
    }


def _run_quantitative_checks(
    listing: Listing, requirement: ExtractedRequirement
) -> dict[str, dict]:
    """Run all algorithmic must-have checks."""
    return {
        "budget": _check_budget(listing, requirement),
        "bedrooms": _check_bedrooms(listing, requirement),
        "bathrooms": _check_bathrooms(listing, requirement),
        "sqft": _check_sqft(listing, requirement),
        "property_type": _check_property_type(listing, requirement),
    }


# ── Semantic must-have filtering ──────────────────────────────────────────

QUANTITATIVE_KEYWORDS = [
    "bedroom",
    "bed",
    "bath",
    "bathroom",
    "budget",
    "price",
    "sqft",
    "square feet",
    "square foot",
    "sq ft",
    "property type",
    "house",
    "condo",
    "townhouse",
]


def _is_quantitative_must_have(must_have: str) -> bool:
    """Heuristic: skip must-haves that overlap with quantitative checks."""
    lower = must_have.lower()
    return any(kw in lower for kw in QUANTITATIVE_KEYWORDS)


def _get_semantic_must_haves(requirement: ExtractedRequirement) -> list[str]:
    """Filter must_haves_list to items needing LLM evaluation."""
    return [
        mh for mh in requirement.must_haves_list if not _is_quantitative_must_have(mh)
    ]


# ── LLM semantic evaluation ──────────────────────────────────────────────


def _listings_to_dicts(listings: list[Listing]) -> list[dict]:
    """Convert Listing ORM objects to dicts for prompt building."""
    return [
        {
            "id": listing.id,
            "address": listing.address,
            "price": listing.price,
            "bedrooms": listing.bedrooms,
            "bathrooms": listing.bathrooms,
            "sqft": listing.sqft,
            "property_type": listing.property_type,
            "description": listing.description,
            "neighborhood": listing.neighborhood,
            "year_built": listing.year_built,
            "days_on_market": listing.days_on_market,
        }
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

MUST_HAVE_WEIGHT = 10
NICE_TO_HAVE_WEIGHT = 7

# Penalty multiplier applied in strict mode when any must-have fails
_STRICT_PENALTY = 0.3



# Mapping from quantitative check names to weight adjustment boost keys
_CHECK_TO_BOOST_KEY: dict[str, str] = {
    "budget": "price_weight_boost",
    "bedrooms": "layout_weight_boost",
    "bathrooms": "layout_weight_boost",
    "sqft": "lot_size_weight_boost",
    "property_type": "location_weight_boost",
}

# Keywords used to map semantic must-have/nice-to-have text to boost keys
_SEMANTIC_BOOST_KEYWORDS: list[tuple[list[str], str]] = [
    (["location", "neighborhood", "area", "commut", "transit", "district"], "location_weight_boost"),
    (["price", "budget", "cost", "afford"], "price_weight_boost"),
    (["lot", "yard", "land", "acreage"], "lot_size_weight_boost"),
    (["layout", "room", "bedroom", "bathroom", "floor plan", "open concept"], "layout_weight_boost"),
    (["basement", "cellar", "lower level"], "basement_weight_boost"),
]


def _get_semantic_boost_key(text: str) -> str | None:
    """Return the boost key for a semantic must-have/nice-to-have text, or None."""
    lower = text.lower()
    for keywords, boost_key in _SEMANTIC_BOOST_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return boost_key
    return None


def _compute_scores(
    listing: Listing,
    quant_checks: dict[str, dict],
    semantic_must_haves: list[str],
    nice_to_haves: list[str],
    llm_result: dict[str, Any] | None,
    scoring_mode: str = "strict",
    weight_adjustments: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Combine quantitative and semantic results into final scores.

    Args:
        scoring_mode: ``"strict"`` (default) applies a heavy penalty when any
            must-have fails.  ``"flexible"`` uses a pure weighted average.
        weight_adjustments: Optional dict of boost multipliers from rejection
            learning (e.g. ``{"price_weight_boost": 1.25}``).  When provided,
            the *importance* of matching criteria is increased – individual
            criterion scores are still capped at 1.0.
    """
    listing_id_str = str(listing.id)
    adj = weight_adjustments or {}

    # ── Must-have evaluation ──
    all_must_have_checks: dict[str, dict] = dict(quant_checks)

    if llm_result and listing_id_str in llm_result:
        listing_llm = llm_result[listing_id_str]
        semantic_checks = listing_llm.get("must_have_checks", {})
        for mh_text in semantic_must_haves:
            if mh_text in semantic_checks:
                all_must_have_checks[mh_text] = semantic_checks[mh_text]
            else:
                all_must_have_checks[mh_text] = {
                    "pass": False,
                    "reason": "Not evaluated by LLM",
                }
    elif semantic_must_haves:
        # LLM failed — default semantic must-haves to pass (graceful fallback)
        for mh_text in semantic_must_haves:
            all_must_have_checks[mh_text] = {
                "pass": True,
                "reason": "LLM unavailable; defaulting to pass",
            }

    must_have_pass = all(c["pass"] for c in all_must_have_checks.values())

    # Compute weighted must-have satisfaction using boost multipliers
    total_mh = len(all_must_have_checks)
    if total_mh > 0:
        weighted_mh_sum = 0.0
        total_mh_weight = 0.0
        for check_name, check in all_must_have_checks.items():
            boost_key = _CHECK_TO_BOOST_KEY.get(check_name) or _get_semantic_boost_key(check_name)
            boost = adj.get(boost_key, 1.0) if boost_key else 1.0
            weighted_mh_sum += (1.0 if check["pass"] else 0.0) * boost
            total_mh_weight += boost
        must_have_satisfaction = weighted_mh_sum / total_mh_weight
    else:
        must_have_satisfaction = 1.0

    # ── Nice-to-have evaluation ──
    nice_to_have_details: dict[str, dict] = {}

    if llm_result and listing_id_str in llm_result:
        listing_llm = llm_result[listing_id_str]
        nth_scores = listing_llm.get("nice_to_have_scores", {})
        for nth_text in nice_to_haves:
            if nth_text in nth_scores:
                nice_to_have_details[nth_text] = nth_scores[nth_text]
            else:
                nice_to_have_details[nth_text] = {
                    "score": 0.5,
                    "reason": "Not evaluated",
                }
    elif nice_to_haves:
        for nth_text in nice_to_haves:
            nice_to_have_details[nth_text] = {
                "score": 0.5,
                "reason": "LLM unavailable; default score",
            }

    # Compute weighted nice-to-have satisfaction using boost multipliers
    if nice_to_have_details:
        weighted_nth_sum = 0.0
        total_nth_weight = 0.0
        for nth_name, detail in nice_to_have_details.items():
            score = min(detail.get("score", 0.5), 1.0)
            boost_key = _get_semantic_boost_key(nth_name)
            boost = adj.get(boost_key, 1.0) if boost_key else 1.0
            weighted_nth_sum += score * boost
            total_nth_weight += boost
        nice_to_have_satisfaction = weighted_nth_sum / total_nth_weight
    else:
        nice_to_have_satisfaction = 1.0

    # ── Overall score (weighted average) ──
    overall_score = (
        must_have_satisfaction * MUST_HAVE_WEIGHT
        + nice_to_have_satisfaction * NICE_TO_HAVE_WEIGHT
    ) / (MUST_HAVE_WEIGHT + NICE_TO_HAVE_WEIGHT)

    # In strict mode, apply a heavy penalty when any must-have fails
    if scoring_mode == "strict" and not must_have_pass:
        overall_score *= _STRICT_PENALTY

    breakdown: dict[str, Any] = {
        "must_have_checks": all_must_have_checks,
        "nice_to_have_details": nice_to_have_details,
        "must_have_rate": round(must_have_satisfaction, 4),
        "must_have_satisfaction": round(must_have_satisfaction, 4),
        "nice_to_have_satisfaction": round(nice_to_have_satisfaction, 4),
        "scoring_mode": scoring_mode,
        "weights": {
            "must_have": MUST_HAVE_WEIGHT,
            "nice_to_have": NICE_TO_HAVE_WEIGHT,
        },
    }

    if adj:
        breakdown["weight_adjustments"] = adj

    return {
        "overall_score": round(overall_score, 4),
        "must_have_pass": must_have_pass,
        "nice_to_have_score": round(nice_to_have_satisfaction, 4),
        "score_breakdown": breakdown,
    }


# ── Public API ────────────────────────────────────────────────────────────


async def rank_results(
    db: Session,
    pipeline_run_id: int,
    requirement: ExtractedRequirement,
    listings: list[Listing],
    llm: LLMProvider,
    scoring_mode: str = "strict",
    weight_adjustments: dict[str, float] | None = None,
) -> list[RankedResult]:
    """Score, rank, and persist RankedResult records.

    Args:
        scoring_mode: ``"strict"`` (default) or ``"flexible"``.
        weight_adjustments: Optional boost multipliers from rejection learning.

    Returns list of RankedResult ORM objects sorted by score descending.
    """
    if not listings:
        return []

    semantic_must_haves = _get_semantic_must_haves(requirement)
    nice_to_haves = requirement.nice_to_haves_list

    logger.info(
        "Ranking %d listings: %d quantitative checks, %d semantic must-haves, %d nice-to-haves",
        len(listings),
        5,
        len(semantic_must_haves),
        len(nice_to_haves),
    )

    # Phase 1: Quantitative checks (instant)
    quant_results: dict[int, dict[str, dict]] = {}
    for listing in listings:
        quant_results[listing.id] = _run_quantitative_checks(listing, requirement)

    # Phase 2: Semantic evaluation (single batched LLM call)
    llm_result = await _evaluate_semantic(
        llm, semantic_must_haves, nice_to_haves, listings
    )

    # Phase 3: Compute final scores
    scored: list[tuple[Listing, dict[str, Any]]] = []
    for listing in listings:
        scores = _compute_scores(
            listing,
            quant_results[listing.id],
            semantic_must_haves,
            nice_to_haves,
            llm_result,
            scoring_mode=scoring_mode,
            weight_adjustments=weight_adjustments,
        )
        scored.append((listing, scores))

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
