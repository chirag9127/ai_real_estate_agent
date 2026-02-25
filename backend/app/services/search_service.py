"""Property search service using multiple real estate scrapers."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.requirement import ExtractedRequirement
from app.services.scrapers.base_scraper import BaseScraper, ScraperError
from app.services.scrapers.registry import ScraperRegistry
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

    # Price -- prefer numeric unformattedPrice
    price = prop.get("unformattedPrice")
    if price is None:
        price = _parse_int_from_string(prop.get("price"))

    # Beds / baths -- use None-safe fallback to preserve 0 (studios)
    beds = prop.get("beds")
    if beds is None:
        beds = prop.get("bedrooms")
    baths = prop.get("baths")
    if baths is None:
        baths = prop.get("bathrooms")

    # Square footage -- may be string like "1,010 sqft"
    living_area = prop.get("livingArea")
    if living_area is None:
        living_area = prop.get("area")
    sqft = _parse_int_from_string(living_area)

    # Days on market -- may be string like "1 day"
    days = _parse_int_from_string(prop.get("daysOnZillow"))

    # Coordinates -- use None-safe fallback to preserve 0.0
    lat_long = prop.get("latLong") or {}
    latitude = lat_long.get("latitude")
    if latitude is None:
        latitude = prop.get("latitude")
    longitude = lat_long.get("longitude")
    if longitude is None:
        longitude = prop.get("longitude")

    # Listing URL -- may be relative
    detail_url = prop.get("detailUrl") or ""
    if detail_url and not detail_url.startswith("http"):
        detail_url = f"https://www.zillow.com{detail_url}"

    # External ID
    ext_id = prop.get("id")
    if ext_id is None:
        ext_id = prop.get("zpid")

    # Home type
    home_type = prop.get("homeType", "")
    if home_type:
        home_type = home_type.lower().replace("_", " ")

    return Listing(
        external_id=str(ext_id) if ext_id else None,
        pipeline_run_id=pipeline_run_id,
        requirement_id=requirement_id,
        source=prop.get("source", "Zillow"),
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
        listing_url=detail_url or None,
        data_json=json.dumps(prop),
    )


def _map_generic_prop_to_listing(
    prop: dict[str, Any],
    pipeline_run_id: int | None,
    requirement_id: int,
) -> Listing:
    """Transform a normalized property dict from any scraper into a Listing ORM object.

    All non-Zillow scrapers return a standardized dict with keys:
    id, source, address, price, bedrooms, bathrooms, sqft, property_type,
    description, image_url, listing_url, latitude, longitude, neighborhood,
    days_on_market, year_built.
    """
    # Parse price if it's a string
    price = prop.get("price")
    if isinstance(price, str):
        try:
            price = float(price.replace("$", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            price = None

    # Parse beds/baths
    beds = prop.get("bedrooms")
    baths = prop.get("bathrooms")

    return Listing(
        external_id=str(prop.get("id", "")) or None,
        pipeline_run_id=pipeline_run_id,
        requirement_id=requirement_id,
        source=prop.get("source", ""),
        address=prop.get("address", ""),
        price=float(price) if price is not None else None,
        bedrooms=int(beds) if beds is not None else None,
        bathrooms=float(baths) if baths is not None else None,
        sqft=_parse_int_from_string(prop.get("sqft")),
        property_type=prop.get("property_type") or None,
        description=prop.get("description", ""),
        neighborhood=prop.get("neighborhood", ""),
        image_url=prop.get("image_url") or None,
        year_built=prop.get("year_built"),
        days_on_market=_parse_int_from_string(prop.get("days_on_market")),
        latitude=prop.get("latitude"),
        longitude=prop.get("longitude"),
        listing_url=prop.get("listing_url") or None,
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
            source="mock",
            **mock,
        )
        db.add(listing)
        listings.append(listing)
    db.commit()
    for listing in listings:
        db.refresh(listing)
    return listings


async def _run_scraper(
    scraper: BaseScraper,
    source_name: str,
    location: str,
    *,
    max_price: int | None = None,
    beds_min: int | None = None,
    baths_min: int | None = None,
    sqft_min: int | None = None,
) -> list[dict[str, Any]]:
    """Run a single scraper, catching and logging errors."""
    try:
        results = await scraper.search(
            location,
            max_price=max_price,
            beds_min=beds_min,
            baths_min=baths_min,
            sqft_min=sqft_min,
        )
        logger.info(
            "%s returned %d results for '%s'",
            source_name, len(results), location,
        )
        return results
    except ScraperError as e:
        logger.error("%s search failed for '%s': %s", source_name, location, e)
        return []
    except Exception as e:
        logger.error(
            "Unexpected error from %s for '%s': %s",
            source_name, location, e, exc_info=True,
        )
        return []


async def search_listings(
    db: Session,
    requirement_id: int,
    pipeline_run_id: int | None = None,
) -> list[Listing]:
    """
    Search for listings matching the given requirement across all scrapers.

    1. Loads the ExtractedRequirement from DB
    2. Initializes all available scrapers via the registry
    3. For each location, runs all scrapers concurrently
    4. Maps results to Listing ORM objects and persists them
    5. Returns the list of created Listing objects
    6. Falls back to mock data if no scrapers return results
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
        logger.warning(
            "No locations for requirement %s, using broad fallback",
            requirement_id,
        )
        locations = ["United States"]

    # Get all available scrapers
    scrapers = ScraperRegistry.get_all_scrapers()
    if not scrapers:
        logger.warning("No scrapers available, falling back to mock data")
        return _create_mock_listings(db, pipeline_run_id, requirement_id)

    logger.info(
        "Running %d scrapers for %d locations: %s",
        len(scrapers),
        len(locations),
        [name for name, _ in scrapers],
    )

    all_listings: list[Listing] = []

    for location in locations:
        # Run all scrapers concurrently for this location
        tasks = [
            _run_scraper(
                scraper,
                source_name,
                location,
                max_price=max_price,
                beds_min=requirement.min_beds if requirement.min_beds else None,
                baths_min=requirement.min_baths if requirement.min_baths else None,
                sqft_min=requirement.min_sqft if requirement.min_sqft else None,
            )
            for source_name, scraper in scrapers
        ]
        results_per_scraper = await asyncio.gather(*tasks)

        for (source_name, _scraper), results in zip(scrapers, results_per_scraper):
            for prop in results:
                # Use Zillow-specific mapper for Zillow results (different format)
                if source_name == "Zillow":
                    listing = _map_zillow_prop_to_listing(
                        prop,
                        pipeline_run_id=pipeline_run_id,
                        requirement_id=requirement_id,
                    )
                else:
                    listing = _map_generic_prop_to_listing(
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
        logger.warning("No results from any scraper, falling back to mock data")
        all_listings = _create_mock_listings(db, pipeline_run_id, requirement_id)

    logger.info(
        "Search complete: %d listings for requirement %s",
        len(all_listings), requirement_id,
    )
    return all_listings
