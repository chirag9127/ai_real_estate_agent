"""Property.ca scraper for Canadian residential real estate data.

Property.ca is a Canadian real estate search platform with listings from
multiple sources. This scraper uses their internal API endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.scrapers.base_scraper import BaseScraper, ScraperError
from app.services.scrapers.utils import (
    build_browser_headers,
    canadian_city_slug,
    parse_standard_listing,
)

logger = logging.getLogger(__name__)

# Property.ca internal search API
_PROPERTY_CA_API_URL = "https://www.property.ca/api/search"

_HEADERS = build_browser_headers(referer="https://www.property.ca/")


class PropertyCaScraper(BaseScraper):
    """Property.ca property scraper for Canadian real estate."""

    SOURCE_NAME = "Property.ca"

    def __init__(self, timeout: float = 30.0) -> None:
        super().__init__()
        self._timeout = timeout
        self._base_url = "https://www.property.ca"

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
        Search Property.ca for properties via their internal API.

        Args:
            location: Canadian city, postal code, or region
            max_price: Maximum price filter
            beds_min: Minimum bedrooms
            baths_min: Minimum bathrooms
            sqft_min: Minimum square footage
            **kwargs: Additional parameters

        Returns:
            List of normalized property dicts.
        """
        logger.info(
            "Searching Property.ca: location=%s, max_price=%s, beds=%s, baths=%s",
            location, max_price, beds_min, baths_min,
        )

        slug = canadian_city_slug(location)

        params: dict[str, Any] = {
            "city": slug,
            "type": "sale",
            "page": kwargs.get("page", 1),
            "limit": 40,
        }

        if max_price is not None:
            params["maxPrice"] = max_price
        if beds_min is not None:
            params["minBedrooms"] = beds_min
        if baths_min is not None:
            params["minBathrooms"] = baths_min
        if sqft_min is not None:
            params["minSqft"] = sqft_min

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers=_HEADERS,
            ) as client:
                response = await client.get(
                    _PROPERTY_CA_API_URL,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "Property.ca HTTP error: %s -- %s",
                e.response.status_code,
                e.response.text[:200],
            )
            raise ScraperError(
                f"Property.ca returned {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            logger.error("Property.ca request error: %s", e)
            raise ScraperError(f"Property.ca request failed: {e}") from e

        raw_listings = data.get("listings", data.get("results", []))
        if not raw_listings:
            logger.warning("Property.ca returned no results for '%s'", location)
            return []

        results = [
            parse_standard_listing(prop, self.SOURCE_NAME, self._base_url)
            for prop in raw_listings
        ]

        logger.info(
            "Property.ca returned %d results for '%s'",
            len(results), location,
        )
        return results
