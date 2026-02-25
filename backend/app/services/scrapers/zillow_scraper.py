"""Zillow scraper using RapidAPI real-estate101 endpoint."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings
from app.services.scrapers.base_scraper import BaseScraper, ScraperError

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "AIRealEstateAgent/1.0"}


def _location_to_zillow_slug(location: str) -> str:
    """Convert a location string like 'New York, NY' into a Zillow URL slug like 'new-york-ny'."""
    slug = location.lower().strip()
    slug = slug.replace(".", "")
    slug = re.sub(r"[,]+", " ", slug)
    slug = re.sub(r"\s+", " ", slug).strip()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


async def _geocode_location(
    location: str,
    http_client: httpx.AsyncClient,
) -> dict[str, float] | None:
    """Geocode a location string via Nominatim and return map bounds."""
    try:
        response = await http_client.get(
            NOMINATIM_URL,
            params={"q": location, "format": "json", "limit": "1"},
            headers=NOMINATIM_HEADERS,
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Geocoding failed for '%s': %s", location, e)
        return None

    if not data:
        logger.warning("No geocoding results for '%s'", location)
        return None

    bbox = data[0].get("boundingbox")
    if not bbox or len(bbox) < 4:
        return None

    return {
        "south": float(bbox[0]),
        "north": float(bbox[1]),
        "west": float(bbox[2]),
        "east": float(bbox[3]),
    }


def build_zillow_search_url(
    location: str,
    *,
    map_bounds: dict[str, float] | None = None,
    max_price: int | None = None,
    beds_min: int | None = None,
    baths_min: int | None = None,
    sqft_min: int | None = None,
) -> str:
    """Build a Zillow search URL with searchQueryState for the given location and filters."""
    slug = _location_to_zillow_slug(location)

    filter_state: dict[str, Any] = {
        "sort": {"value": "globalrelevanceex"},
    }
    if max_price is not None:
        filter_state["price"] = {"max": max_price}
    if beds_min is not None:
        filter_state["beds"] = {"min": beds_min}
    if baths_min is not None:
        filter_state["baths"] = {"min": baths_min}
    if sqft_min is not None:
        filter_state["sqft"] = {"min": sqft_min}

    search_query_state: dict[str, Any] = {
        "isMapVisible": True,
        "isListVisible": True,
        "filterState": filter_state,
        "usersSearchTerm": location,
    }

    if map_bounds:
        search_query_state["mapBounds"] = map_bounds

    encoded_state = quote(json.dumps(search_query_state, separators=(",", ":")))
    return f"https://www.zillow.com/{slug}/?searchQueryState={encoded_state}"


class ZillowScraper(BaseScraper):
    """Zillow property scraper using RapidAPI real-estate101 endpoint."""

    SOURCE_NAME = "Zillow"

    def __init__(self, api_key: str | None = None, host: str | None = None) -> None:
        super().__init__()
        key = api_key or settings.rapidapi_key
        if not key:
            raise ScraperError("RAPIDAPI_KEY is not configured")
        self._host = host or settings.rapidapi_zillow_host
        self._headers = {
            "x-rapidapi-key": key,
            "x-rapidapi-host": self._host,
        }
        self._base_url = f"https://{self._host}"

    async def search(
        self,
        location: str,
        *,
        max_price: int | None = None,
        beds_min: int | None = None,
        baths_min: int | None = None,
        sqft_min: int | None = None,
        page: int = 1,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Search Zillow for properties."""
        async with httpx.AsyncClient(timeout=30.0) as http:
            # Step 1: Geocode to get map bounds
            map_bounds = await _geocode_location(location, http)
            if not map_bounds:
                logger.error("Could not geocode '%s'", location)
                return []

            # Step 2: Build the Zillow search URL
            zillow_url = build_zillow_search_url(
                location,
                map_bounds=map_bounds,
                max_price=max_price,
                beds_min=beds_min,
                baths_min=baths_min,
                sqft_min=sqft_min,
            )

            api_url = f"{self._base_url}/api/search/byurl"
            params: dict[str, str] = {"url": zillow_url}
            if page > 1:
                params["page"] = str(page)

            logger.info("Zillow API request: %s (location=%s)", api_url, location)

            # Step 3: Call the API
            try:
                response = await http.get(
                    api_url, headers=self._headers, params=params
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.error("Zillow API HTTP error: %s", e.response.status_code)
                raise ScraperError(f"Zillow API returned {e.response.status_code}") from e
            except httpx.RequestError as e:
                logger.error("Zillow API request error: %s", e)
                raise ScraperError(f"Zillow API request failed: {e}") from e

        results = data.get("results", [])
        total = data.get("totalCount", "?")
        logger.info("Zillow API returned %d results (totalCount=%s) for '%s'", len(results), total, location)

        # Add source to each result
        for result in results:
            result["source"] = self.SOURCE_NAME

        return results


# Backward compatibility alias
ZillowAPIError = ScraperError
