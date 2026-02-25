"""Property search service using multiple real estate scrapers."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.requirement import ExtractedRequirement
from app.services.scrapers import ScraperError, ScraperRegistry
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
        "source": "Mock Data",
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
        "source": "Mock Data",
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
        "source": "Mock Data",
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


def _map_property_to_listing(
    prop: dict[str, Any],
    pipeline_run_id: int | None,
    requirement_id: int,
) -> Listing:
    """Transform a property dict (from any scraper) into a Listing ORM object."""
    # Address
    addr = prop.get("address")
    if isinstance(addr, dict):
        parts = [
            addr.get("street", ""),
            addr.get("city", ""),
            addr.get("state", ""),
            addr.get("province", ""),
            addr.get("zipcode", ""),
            addr.get("postal_code", ""),
        ]
        full_address = ", ".join(p for p in parts if p)
        neighborhood = addr.get("city") or addr.get("city_name") or ""
    else:
        full_address = str(addr) if addr else ""
        neighborhood = ""

    # Price
    price = prop.get("unformattedPrice")
    if price is None:
        price = prop.get("price")
    if price is not None and isinstance(price, str):
        price = _parse_int_from_string(price)

    # Beds / baths
    beds = prop.get("beds") or prop.get("bedrooms")
    baths = prop.get("baths") or prop.get("bathrooms")

    # Square footage
    sqft = _parse_int_from_string(
        prop.get("livingArea") or prop.get("sqft") or prop.get("area")
    )

    # Days on market
    days = _parse_int_from_string(
        prop.get("daysOnZillow") or prop.get("daysOnMarket") or prop.get("dom")
    )

    # Coordinates
    lat_long = prop.get("latLong") or {}
    latitude = lat_long.get("latitude") if isinstance(lat_long, dict) else prop.get("latitude")
    longitude = lat_long.get("longitude") if isinstance(lat_long, dict) else prop.get("longitude")

    # Listing URL
    listing_url = (
        prop.get("listing_url")
        or prop.get("detailUrl")
        or prop.get("url")
        or ""
    )
    
    # External ID
    ext_id = prop.get("id") or prop.get("zpid") or prop.get("external_id")

    # Home type / property type
    home_type = prop.get("property_type") or prop.get("homeType") or prop.get("type") or ""
    if home_type:
        home_type = str(home_type).lower().replace("_", " ")

    # Source - default to Zillow if not provided but has Zillow-specific fields
    source = prop.get("source")
    if not source:
        if prop.get("detailUrl") or prop.get("daysOnZillow") or prop.get("homeType"):
            source = "Zillow"
        else:
            source = "Unknown"
    
    # Make relative URLs absolute for Zillow
    if listing_url and not listing_url.startswith("http"):
        if "zillow" in source.lower():
            listing_url = f"https://www.zillow.com{listing_url}"

    return Listing(
        external_id=str(ext_id) if ext_id else None,
        pipeline_run_id=pipeline_run_id,
        requirement_id=requirement_id,
        source=source,
        address=full_address,
        price=price,
        bedrooms=int(beds) if beds is not None else None,
        bathrooms=float(baths) if baths is not None else None,
        sqft=sqft,
        property_type=home_type or None,
        description=prop.get("description", ""),
        neighborhood=neighborhood,
        image_url=prop.get("image_url") or prop.get("imgSrc") or prop.get("image"),
        year_built=prop.get("yearBuilt") or prop.get("year_built"),
        days_on_market=days,
        latitude=latitude,
        longitude=longitude,
        listing_url=listing_url or None,
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
    Search for listings matching the given requirement using all available scrapers.

    Pipeline:
    1. Loads the ExtractedRequirement from DB
    2. For each location, calls all registered scrapers
    3. Aggregates results from all sources
    4. Maps results to Listing ORM objects and persists them
    5. Returns the list of created Listing objects
    6. Falls back to mock data if all scrapers fail
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
    scrapers = ScraperRegistry.get_all_scrapers()

    for location in locations:
        logger.info(
            "Searching multiple sources: location=%s, max_price=%s, beds=%s, baths=%s, sqft=%s",
            location,
            max_price,
            requirement.min_beds,
            requirement.min_baths,
            requirement.min_sqft,
        )

        for source_name, scraper in scrapers.items():
            try:
                logger.debug("Attempting %s search for %s", source_name, location)
                results = await scraper.search(
                    location=location,
                    max_price=max_price,
                    beds_min=requirement.min_beds if requirement.min_beds else None,
                    baths_min=requirement.min_baths if requirement.min_baths else None,
                    sqft_min=requirement.min_sqft if requirement.min_sqft else None,
                )

                logger.info("%s returned %d results for %s", source_name, len(results), location)

                for prop in results:
                    if "source" not in prop:
                        prop["source"] = source_name

                    listing = _map_property_to_listing(
                        prop,
                        pipeline_run_id=pipeline_run_id,
                        requirement_id=requirement_id,
                    )
                    db.add(listing)
                    all_listings.append(listing)

            except ScraperError as e:
                logger.error("Scraper error for %s at location %s: %s", source_name, location, e)
            except Exception as e:
                logger.exception("Unexpected error during %s search for %s", source_name, location)

        if all_listings:
            db.commit()
            for listing in all_listings:
                db.refresh(listing)

    if not all_listings:
        logger.warning("No results from any scraper, falling back to mock data")
        all_listings = _create_mock_listings(db, pipeline_run_id, requirement_id)

    logger.info(
        "Search complete: %d listings from %d sources for requirement %s",
        len(all_listings),
        len(set(l.source for l in all_listings)),
        requirement_id,
    )
    return all_listings


# Backward compatibility aliases
_map_zillow_prop_to_listing = _map_property_to_listing
