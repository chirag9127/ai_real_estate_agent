"""Condos.ca scraper for Canadian condo real estate data.

Condos.ca specializes in condo properties across Canada.
This scraper uses their internal API endpoints to fetch listings.
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

# Condos.ca internal search API
_CONDOS_CA_API_URL = "https://condos.ca/api/listings"

_HEADERS = build_browser_headers(referer="https://condos.ca/")


class CondosCaScraper(BaseScraper):
    """Condos.ca property scraper for Canadian condos."""

    SOURCE_NAME = "Condos.ca"

    def __init__(self, timeout: float = 30.0) -> None:
        super().__init__()
        self._timeout = timeout
        self._base_url = "https://condos.ca"

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
        Search Condos.ca for condo properties via their internal API.

        Args:
            location: Canadian city or condo project area
            max_price: Maximum price filter
            beds_min: Minimum bedrooms
            baths_min: Minimum bathrooms
            sqft_min: Minimum square footage
            **kwargs: Additional parameters

        Returns:
            List of normalized property dicts.
        """
        logger.info(
            "Searching Condos.ca: location=%s, max_price=%s, beds=%s, baths=%s",
            location, max_price, beds_min, baths_min,
        )

        slug = canadian_city_slug(location)

        params: dict[str, Any] = {
            "city": slug,
            "sale_type": "sale",
            "page": kwargs.get("page", 1),
            "per_page": 40,
        }

        if max_price is not None:
            params["max_price"] = max_price
        if beds_min is not None:
            params["min_beds"] = beds_min
        if baths_min is not None:
            params["min_baths"] = baths_min
        if sqft_min is not None:
            params["min_sqft"] = sqft_min

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                headers=_HEADERS,
            ) as client:
                response = await client.get(
                    _CONDOS_CA_API_URL,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                "Condos.ca HTTP error: %s -- %s",
                e.response.status_code,
                e.response.text[:200],
            )
            raise ScraperError(
                f"Condos.ca returned {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            logger.error("Condos.ca request error: %s", e)
            raise ScraperError(f"Condos.ca request failed: {e}") from e

        raw_listings = data.get("listings", data.get("results", []))
        if not raw_listings:
            logger.warning("Condos.ca returned no results for '%s'", location)
            return []

        results = [
            parse_standard_listing(
                prop, self.SOURCE_NAME, self._base_url,
                default_property_type="condo",
            )
            for prop in raw_listings
        ]

        logger.info(
            "Condos.ca returned %d results for '%s'",
            len(results), location,
        )
        return results
