"""HouseSigma scraper for Canadian real estate data.

HouseSigma is a Canadian real estate search platform. This scraper fetches
property data through their internal API endpoints used by their web app.

Note: HouseSigma may have anti-scraping measures. For production use, consider
respecting rate limits and their terms of service.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.scrapers.base_scraper import BaseScraper, ScraperError
from app.services.scrapers.utils import build_browser_headers, strip_province_suffix, _first_not_none

logger = logging.getLogger(__name__)

# HouseSigma internal API used by their frontend
_HOUSESIGMA_API_URL = "https://housesigma.com/bkv2/api/listing/list"

_HEADERS = build_browser_headers(
    origin="https://housesigma.com",
    referer="https://housesigma.com/",
    content_type="application/json",
)

# Map common location strings to HouseSigma community slugs
_LOCATION_SLUGS: dict[str, str] = {
    "toronto": "toronto",
    "mississauga": "mississauga",
    "brampton": "brampton",
    "markham": "markham",
    "vaughan": "vaughan",
    "richmond hill": "richmond-hill",
    "oakville": "oakville",
    "burlington": "burlington",
    "hamilton": "hamilton",
    "ottawa": "ottawa",
    "vancouver": "vancouver",
    "calgary": "calgary",
    "edmonton": "edmonton",
    "montreal": "montreal",
}


def _location_to_slug(location: str) -> str:
    """Convert a location string to a HouseSigma-compatible slug."""
    city = strip_province_suffix(location).lower().strip()
    return _LOCATION_SLUGS.get(city, city.replace(" ", "-"))


class HouseSigmaScraper(BaseScraper):
    """HouseSigma property scraper for Canadian real estate."""

    SOURCE_NAME = "HouseSigma"

    def __init__(self, timeout: float = 30.0) -> None:
        super().__init__()
        self._timeout = timeout
        self._base_url = "https://housesigma.com"

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
        Search HouseSigma for properties via their internal API.

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
            "Searching HouseSigma: location=%s, max_price=%s, beds=%s, baths=%s",
            location, max_price, beds_min, baths_min,
        )

        slug = _location_to_slug(location)

        # Build the request payload for HouseSigma's internal API
        payload: dict[str, Any] = {
            "community": slug,
            "type": "sale",
            "page": kwargs.get("page", 1),
            "limit": 40,
        }

        if max_price is not None:
            payload["price_max"] = max_price
        if beds_min is not None:
            payload["bedroom_min"] = beds_min
        if baths_min is not None:
            payload["bathroom_min"] = baths_min

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers=_HEADERS,
            ) as client:
                response = await client.post(
                    _HOUSESIGMA_API_URL,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "HouseSigma HTTP error: %s -- %s",
                e.response.status_code,
                e.response.text[:200],
            )
            raise ScraperError(
                f"HouseSigma returned {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            logger.error("HouseSigma request error: %s", e)
            raise ScraperError(f"HouseSigma request failed: {e}") from e

        raw_listings = data.get("data", {}).get("list", [])
        if not raw_listings:
            logger.warning("HouseSigma returned no results for '%s'", location)
            return []

        results: list[dict[str, Any]] = []
        for prop in raw_listings:
            listing_id = prop.get("id_listing") or prop.get("id", "")
            address_parts = [
                prop.get("address", ""),
                prop.get("municipality", ""),
                prop.get("province", ""),
            ]
            full_address = ", ".join(p for p in address_parts if p)

            detail_url = (
                f"{self._base_url}/listing/{listing_id}"
                if listing_id
                else ""
            )

            results.append({
                "id": str(listing_id),
                "source": self.SOURCE_NAME,
                "address": full_address,
                "price": _first_not_none(prop.get("price"), prop.get("list_price")),
                "bedrooms": _first_not_none(prop.get("bedroom"), prop.get("bedrooms")),
                "bathrooms": _first_not_none(prop.get("bathroom"), prop.get("bathrooms")),
                "sqft": _first_not_none(prop.get("sqft"), prop.get("area")),
                "property_type": prop.get("type_name", ""),
                "description": prop.get("description", ""),
                "image_url": prop.get("photo_url") or prop.get("image"),
                "listing_url": detail_url,
                "latitude": prop.get("lat"),
                "longitude": prop.get("lng"),
                "neighborhood": prop.get("municipality", ""),
                "days_on_market": prop.get("dom"),
            })

        logger.info(
            "HouseSigma returned %d results for '%s'",
            len(results), location,
        )
        return results
