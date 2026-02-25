"""Zoocasa scraper for Canadian real estate data.

Zoocasa is a Canadian real estate platform with property listings and market data.
This scraper uses their internal API endpoints to fetch property listings.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.services.scrapers.base_scraper import BaseScraper, ScraperError

logger = logging.getLogger(__name__)

# Zoocasa internal search API (Next.js API route)
_ZOOCASA_API_URL = "https://www.zoocasa.com/api/search"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.zoocasa.com/",
}


def _location_to_zoocasa_slug(location: str) -> str:
    """Convert a location string to a Zoocasa-compatible slug.

    Examples:
        "Toronto, ON" -> "toronto-on"
        "Vancouver, BC" -> "vancouver-bc"
    """
    slug = location.lower().strip()
    slug = slug.replace(".", "")
    slug = re.sub(r"[,]+", " ", slug)
    slug = re.sub(r"\s+", " ", slug).strip()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


class ZoocasaScraper(BaseScraper):
    """Zoocasa property scraper for Canadian real estate."""

    SOURCE_NAME = "Zoocasa"

    def __init__(self, timeout: float = 30.0) -> None:
        super().__init__()
        self._timeout = timeout
        self._base_url = "https://www.zoocasa.com"

    async def search(
        self,
        location: str,
        *,
        max_price: int | None = None,
        beds_min: int | None = None,
        baths_min: int | None = None,
        sqft_min: int | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Search Zoocasa for properties via their internal API.

        Args:
            location: Canadian city or region (e.g., "Toronto, ON")
            max_price: Maximum price filter
            beds_min: Minimum bedrooms
            baths_min: Minimum bathrooms
            sqft_min: Minimum square footage
            **kwargs: Additional parameters

        Returns:
            List of normalized property dicts.
        """
        logger.info(
            "Searching Zoocasa: location=%s, max_price=%s, beds=%s, baths=%s",
            location, max_price, beds_min, baths_min,
        )

        slug = _location_to_zoocasa_slug(location)

        # Build query parameters for Zoocasa's search API
        params: dict[str, Any] = {
            "slug": slug,
            "saleType": "sale",
            "page": kwargs.get("page", 1),
            "limit": 40,
        }

        if max_price is not None:
            params["maxPrice"] = max_price
        if beds_min is not None:
            params["minBeds"] = beds_min
        if baths_min is not None:
            params["minBaths"] = baths_min
        if sqft_min is not None:
            params["minSqft"] = sqft_min

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers=_HEADERS,
            ) as client:
                response = await client.get(
                    _ZOOCASA_API_URL,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "Zoocasa HTTP error: %s -- %s",
                e.response.status_code,
                e.response.text[:200],
            )
            raise ScraperError(
                f"Zoocasa returned {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            logger.error("Zoocasa request error: %s", e)
            raise ScraperError(f"Zoocasa request failed: {e}") from e

        raw_listings = data.get("listings", data.get("results", []))
        if not raw_listings:
            logger.warning("Zoocasa returned no results for '%s'", location)
            return []

        results: list[dict[str, Any]] = []
        for prop in raw_listings:
            listing_id = prop.get("mlsNumber") or prop.get("id", "")
            address = prop.get("address") or prop.get("fullAddress", "")
            if isinstance(address, dict):
                address_parts = [
                    address.get("street", ""),
                    address.get("city", ""),
                    address.get("province", ""),
                    address.get("postalCode", ""),
                ]
                full_address = ", ".join(p for p in address_parts if p)
                neighborhood = address.get("city", "")
            else:
                full_address = str(address) if address else ""
                neighborhood = prop.get("city", "")

            # Build listing URL
            detail_slug = prop.get("slug") or prop.get("detailUrl", "")
            if detail_slug and not detail_slug.startswith("http"):
                listing_url = f"{self._base_url}/{detail_slug.lstrip('/')}"
            elif detail_slug:
                listing_url = detail_slug
            else:
                listing_url = ""

            # Parse price
            price = prop.get("price") or prop.get("listPrice")
            if isinstance(price, str):
                try:
                    price = float(price.replace("$", "").replace(",", "").strip())
                except (ValueError, AttributeError):
                    price = None

            results.append({
                "id": str(listing_id),
                "source": self.SOURCE_NAME,
                "address": full_address,
                "price": price,
                "bedrooms": prop.get("bedrooms") or prop.get("beds"),
                "bathrooms": prop.get("bathrooms") or prop.get("baths"),
                "sqft": prop.get("sqft") or prop.get("squareFeet"),
                "property_type": prop.get("propertyType") or prop.get("type", ""),
                "description": prop.get("description", ""),
                "image_url": prop.get("imageUrl") or prop.get("photo", ""),
                "listing_url": listing_url,
                "latitude": prop.get("latitude") or prop.get("lat"),
                "longitude": prop.get("longitude") or prop.get("lng"),
                "neighborhood": neighborhood,
                "days_on_market": prop.get("daysOnMarket"),
            })

        logger.info(
            "Zoocasa returned %d results for '%s'",
            len(results), location,
        )
        return results
