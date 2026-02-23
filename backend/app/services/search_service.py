"""Property search service using Zillow RapidAPI."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.requirement import ExtractedRequirement
from app.services.zillow_client import ZillowAPIError, ZillowClient
from app.utils.exceptions import RequirementNotFoundError

logger = logging.getLogger(__name__)

MOCK_LISTINGS = [
    {
        "address": "123 Oak Street, Springfield",
        "price": 450000,
        "bedrooms": 3,
        "bathrooms": 2.0,
        "sqft": 1800,
        "property_type": "house",
        "description": "Charming 3-bed home with updated kitchen and large backyard.",
        "neighborhood": "Downtown Springfield",
    },
    {
        "address": "456 Maple Avenue, Springfield",
        "price": 525000,
        "bedrooms": 4,
        "bathrooms": 2.5,
        "sqft": 2200,
        "property_type": "house",
        "description": "Spacious 4-bed colonial with open floor plan near top-rated schools.",
        "neighborhood": "Westside Springfield",
    },
    {
        "address": "789 Pine Court, Shelbyville",
        "price": 380000,
        "bedrooms": 3,
        "bathrooms": 2.0,
        "sqft": 1600,
        "property_type": "townhouse",
        "description": "Modern townhouse with garage, close to transit and shopping.",
        "neighborhood": "Central Shelbyville",
    },
]


def _parse_int_from_string(value: Any) -> int | None:
    """Extract an integer from a string like '1,010 sqft' or '1 day'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"[\d,]+", str(value))
    if match:
        return int(match.group().replace(",", ""))
    return None


def _map_zillow_prop_to_listing(
    prop: dict[str, Any],
    pipeline_run_id: int | None,
    requirement_id: int,
) -> Listing:
    """Transform a single Zillow property dict into a Listing ORM object.

    Handles the real-estate101 API response format where:
    - address is {street, city, state, zipcode}
    - price is formatted string, unformattedPrice is numeric
    - beds/baths instead of bedrooms/bathrooms
    - livingArea is a string like "1,010 sqft"
    - daysOnZillow is a string like "1 day"
    - latLong is {latitude, longitude}
    - detailUrl may be relative ("/homedetails/...")
    - homeType is uppercase like "SINGLE_FAMILY"
    """
    # Address
    addr = prop.get("address")
    if isinstance(addr, dict):
        parts = [
            addr.get("street", ""),
            addr.get("city", ""),
            addr.get("state", ""),
            addr.get("zipcode", ""),
        ]
        full_address = ", ".join(p for p in parts if p)
        neighborhood = addr.get("city", "")
    else:
        full_address = str(addr) if addr else ""
        neighborhood = ""

    # Price — prefer numeric unformattedPrice
    price = prop.get("unformattedPrice")
    if price is None:
        price = _parse_int_from_string(prop.get("price"))

    # Beds / baths
    beds = prop.get("beds") or prop.get("bedrooms")
    baths = prop.get("baths") or prop.get("bathrooms")

    # Square footage — may be string like "1,010 sqft"
    sqft = _parse_int_from_string(prop.get("livingArea") or prop.get("area"))

    # Days on market — may be string like "1 day"
    days = _parse_int_from_string(prop.get("daysOnZillow"))

    # Coordinates
    lat_long = prop.get("latLong") or {}
    latitude = lat_long.get("latitude") or prop.get("latitude")
    longitude = lat_long.get("longitude") or prop.get("longitude")

    # Zillow URL — may be relative
    detail_url = prop.get("detailUrl") or ""
    if detail_url and not detail_url.startswith("http"):
        detail_url = f"https://www.zillow.com{detail_url}"

    # External ID
    ext_id = prop.get("id") or prop.get("zpid")

    # Home type
    home_type = prop.get("homeType", "")
    if home_type:
        home_type = home_type.lower().replace("_", " ")

    return Listing(
        external_id=str(ext_id) if ext_id else None,
        pipeline_run_id=pipeline_run_id,
        requirement_id=requirement_id,
        address=full_address,
        price=price,
        bedrooms=int(beds) if beds is not None else None,
        bathrooms=float(baths) if baths is not None else None,
        sqft=sqft,
        property_type=home_type or None,
        description=prop.get("description", ""),
        neighborhood=neighborhood,
        image_url=prop.get("imgSrc") or prop.get("hiResImageLink"),
        year_built=prop.get("yearBuilt"),
        days_on_market=days,
        latitude=latitude,
        longitude=longitude,
        zillow_url=detail_url or None,
        data_json=json.dumps(prop),
    )


def _create_mock_listings(
    db: Session,
    pipeline_run_id: int | None,
    requirement_id: int,
) -> list[Listing]:
    """Create listings from mock data as a fallback."""
    listings: list[Listing] = []
    for mock in MOCK_LISTINGS:
        listing = Listing(
            pipeline_run_id=pipeline_run_id,
            requirement_id=requirement_id,
            **mock,
        )
        db.add(listing)
        listings.append(listing)
    db.commit()
    for listing in listings:
        db.refresh(listing)
    return listings


async def search_listings(
    db: Session,
    requirement_id: int,
    pipeline_run_id: int | None = None,
) -> list[Listing]:
    """
    Search for listings matching the given requirement.

    1. Loads the ExtractedRequirement from DB
    2. For each location, calls Zillow search_by_url
    3. Maps results to Listing ORM objects and persists them
    4. Returns the list of created Listing objects
    5. Falls back to mock data if API is unavailable
    """
    requirement = (
        db.query(ExtractedRequirement)
        .filter(ExtractedRequirement.id == requirement_id)
        .first()
    )
    if not requirement:
        raise RequirementNotFoundError(f"Requirement {requirement_id} not found")

    max_price = int(requirement.budget_max) if requirement.budget_max else None

    locations = requirement.locations_list
    if not locations:
        logger.warning("No locations for requirement %s, using broad fallback", requirement_id)
        locations = ["United States"]

    all_listings: list[Listing] = []

    try:
        client = ZillowClient()

        for location in locations:
            logger.info(
                "Searching Zillow: location=%s, max_price=%s, beds=%s, baths=%s, sqft=%s",
                location, max_price, requirement.min_beds, requirement.min_baths, requirement.min_sqft,
            )
            try:
                results = await client.search_by_url(
                    location=location,
                    max_price=max_price,
                    beds_min=requirement.min_beds if requirement.min_beds else None,
                    baths_min=requirement.min_baths if requirement.min_baths else None,
                    sqft_min=requirement.min_sqft if requirement.min_sqft else None,
                )
            except ZillowAPIError as e:
                logger.error("Zillow search failed for location %s: %s", location, e)
                continue

            for prop in results:
                listing = _map_zillow_prop_to_listing(
                    prop,
                    pipeline_run_id=pipeline_run_id,
                    requirement_id=requirement_id,
                )
                db.add(listing)
                all_listings.append(listing)

        if all_listings:
            db.commit()
            for listing in all_listings:
                db.refresh(listing)
        else:
            logger.warning("No Zillow results, falling back to mock data")
            all_listings = _create_mock_listings(db, pipeline_run_id, requirement_id)

    except ZillowAPIError as e:
        logger.error("Zillow client init failed: %s — falling back to mock data", e)
        all_listings = _create_mock_listings(db, pipeline_run_id, requirement_id)

    logger.info("Search complete: %d listings for requirement %s", len(all_listings), requirement_id)
    return all_listings
