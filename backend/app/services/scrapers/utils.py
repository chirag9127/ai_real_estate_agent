"""Shared utilities for real estate scrapers."""

from __future__ import annotations

import re
from typing import Any


# Common Canadian province suffixes to strip from location strings
_PROVINCE_SUFFIXES = [
    ", on", ", ontario",
    ", bc", ", british columbia",
    ", ab", ", alberta",
    ", qc", ", quebec",
    ", mb", ", manitoba",
    ", sk", ", saskatchewan",
    ", ns", ", nova scotia",
    ", nb", ", new brunswick",
    ", nl", ", newfoundland and labrador",
    ", pe", ", prince edward island",
]


def strip_province_suffix(location: str) -> str:
    """Strip Canadian province suffixes from a location string.

    Examples:
        "Toronto, ON" -> "Toronto"
        "Vancouver, British Columbia" -> "Vancouver"
        "New York, NY" -> "New York, NY"  (no match)
    """
    normalized = location.lower().strip()
    for suffix in _PROVINCE_SUFFIXES:
        if normalized.endswith(suffix):
            return location[: len(location) - len(suffix)].strip()
    return location.strip()


def slugify(location: str) -> str:
    """Convert a location string into a URL-friendly slug.

    Examples:
        "New York, NY" -> "new-york-ny"
        "San Francisco, CA" -> "san-francisco-ca"
        "Washington D.C." -> "washington-dc"
    """
    slug = location.lower().strip()
    slug = slug.replace(".", "")
    slug = re.sub(r"[,]+", " ", slug)
    slug = re.sub(r"\s+", " ", slug).strip()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def canadian_city_slug(location: str) -> str:
    """Convert a Canadian location to a city-only slug (strips province).

    Examples:
        "Toronto, ON" -> "toronto"
        "Richmond Hill, Ontario" -> "richmond-hill"
    """
    city = strip_province_suffix(location)
    return slugify(city)


def build_browser_headers(
    *,
    origin: str = "",
    referer: str = "",
    content_type: str | None = None,
) -> dict[str, str]:
    """Build common browser-like HTTP headers for scraping.

    Args:
        origin: Origin header value (e.g., "https://housesigma.com")
        referer: Referer header value (e.g., "https://housesigma.com/")
        content_type: Optional Content-Type header
    """
    headers: dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if origin:
        headers["Origin"] = origin
    if referer:
        headers["Referer"] = referer
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def parse_standard_listing(
    prop: dict[str, Any],
    source_name: str,
    base_url: str,
    *,
    default_property_type: str = "",
) -> dict[str, Any]:
    """Parse a standard property dict from a Canadian real estate API response.

    This handles the common response format shared by Zoocasa, Condos.ca,
    and Property.ca where properties have mlsNumber, address (dict or string),
    slug-based detail URLs, and standard field names.

    Args:
        prop: Raw property dict from the API
        source_name: Name of the source (e.g., "Zoocasa")
        base_url: Base URL for building listing URLs (e.g., "https://condos.ca")
        default_property_type: Fallback property type if not in data

    Returns:
        Normalized property dict with standard keys.
    """
    listing_id = prop.get("mlsNumber") or prop.get("id", "")

    # Parse address (dict or string)
    address = prop.get("address", "")
    if isinstance(address, dict):
        address_parts = [
            address.get("street", ""),
            address.get("city", ""),
            address.get("province", ""),
            address.get("postalCode", ""),
        ]
        full_address = ", ".join(p for p in address_parts if p)
        neighborhood = (
            address.get("neighborhood")
            or address.get("city", "")
        )
    else:
        full_address = str(address) if address else ""
        neighborhood = prop.get("neighborhood") or prop.get("city", "")

    # Build listing URL from slug
    detail_slug = prop.get("slug") or prop.get("url") or prop.get("detailUrl", "")
    if detail_slug and not detail_slug.startswith("http"):
        listing_url = f"{base_url}/{detail_slug.lstrip('/')}"
    elif detail_slug:
        listing_url = detail_slug
    else:
        listing_url = ""

    # Parse price (may be numeric or string like "$1,200,000")
    price = prop.get("price") or prop.get("listPrice")
    if isinstance(price, str):
        try:
            price = float(price.replace("$", "").replace(",", "").strip())
        except (ValueError, AttributeError):
            price = None

    return {
        "id": str(listing_id),
        "source": source_name,
        "address": full_address,
        "price": price,
        "bedrooms": prop.get("bedrooms") or prop.get("beds"),
        "bathrooms": prop.get("bathrooms") or prop.get("baths"),
        "sqft": prop.get("sqft") or prop.get("squareFeet"),
        "property_type": prop.get("propertyType") or prop.get("type", default_property_type),
        "description": prop.get("description", ""),
        "image_url": prop.get("imageUrl") or prop.get("photo", ""),
        "listing_url": listing_url,
        "latitude": prop.get("latitude") or prop.get("lat"),
        "longitude": prop.get("longitude") or prop.get("lng"),
        "neighborhood": neighborhood,
        "days_on_market": prop.get("daysOnMarket"),
        "year_built": prop.get("yearBuilt"),
    }
