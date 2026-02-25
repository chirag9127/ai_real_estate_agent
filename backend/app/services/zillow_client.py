"""Zillow RapidAPI client for property search via real-estate101."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "AIRealEstateAgent/1.0"}

# Default maximum number of concurrent API requests
DEFAULT_MAX_CONCURRENCY = 5


class ZillowAPIError(Exception):
    """Raised when the Zillow API returns an error or is unreachable."""
    pass


def _location_to_zillow_slug(location: str) -> str:
    """
    Convert a location string like "New York, NY" into a Zillow URL slug
    like "new-york-ny".
    """
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
    """
    Geocode a location string via Nominatim (OpenStreetMap) and return
    map bounds as {"north", "south", "east", "west"}.

    Returns None if geocoding fails.
    """
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

    # boundingbox is [south, north, west, east] as strings
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
    """
    Build a Zillow search URL with searchQueryState for the given location
    and filters.  The API requires mapBounds to return results.
    """
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


class ZillowClient:
    """HTTP client for Zillow property search via RapidAPI (real-estate101).

    Supports use as an async context manager to share a single
    ``httpx.AsyncClient`` across multiple concurrent searches::

        async with ZillowClient() as client:
            results = await asyncio.gather(
                client.search_by_url("New York, NY"),
                client.search_by_url("Chicago, IL"),
            )

    Can also be used without the context manager for backward compatibility
    (a fresh ``httpx.AsyncClient`` is created per request in that case).
    """

    def __init__(
        self,
        api_key: str | None = None,
        host: str | None = None,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ) -> None:
        key = api_key or settings.rapidapi_key
        if not key:
            raise ZillowAPIError("RAPIDAPI_KEY is not configured")
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self._host = host or settings.rapidapi_zillow_host
        self._headers = {
            "x-rapidapi-key": key,
            "x-rapidapi-host": self._host,
        }
        self._base_url = f"https://{self._host}"
        self._semaphore = asyncio.Semaphore(max_concurrency)
        # Serialize Nominatim geocode calls to respect its 1 req/s policy
        self._geocode_lock = asyncio.Lock()
        # Shared HTTP client — set when used as async context manager
        self._shared_http: httpx.AsyncClient | None = None

    # -- async context manager -------------------------------------------------

    async def __aenter__(self) -> ZillowClient:
        if self._shared_http is not None:
            raise RuntimeError("ZillowClient context manager is not reentrant")
        self._shared_http = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._shared_http is not None:
            await self._shared_http.aclose()
            self._shared_http = None

    # -- public API ------------------------------------------------------------

    async def search_by_url(
        self,
        location: str,
        *,
        max_price: int | None = None,
        beds_min: int | None = None,
        baths_min: int | None = None,
        sqft_min: int | None = None,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Search Zillow for properties:
        1. Geocodes the location to get map bounds (via Nominatim)
        2. Builds a Zillow search URL with searchQueryState
        3. Calls the /api/search/byurl endpoint

        Returns list of property dicts from the "results" key.

        When the client is used as an async context manager the shared
        ``httpx.AsyncClient`` is reused and a semaphore limits concurrency.
        Otherwise a one-off client is created for backward compatibility.
        """
        async with self._semaphore, self._http_client() as http:
            return await self._do_search(
                http, location,
                max_price=max_price, beds_min=beds_min,
                baths_min=baths_min, sqft_min=sqft_min, page=page,
            )

    # -- internals -------------------------------------------------------------

    @contextlib.asynccontextmanager
    async def _http_client(self) -> AsyncIterator[httpx.AsyncClient]:
        """Yield the shared HTTP client, or a temporary one-off client."""
        if self._shared_http is not None:
            yield self._shared_http
        else:
            async with httpx.AsyncClient(timeout=30.0) as http:
                yield http

    async def _do_search(
        self,
        http: httpx.AsyncClient,
        location: str,
        *,
        max_price: int | None = None,
        beds_min: int | None = None,
        baths_min: int | None = None,
        sqft_min: int | None = None,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Execute the geocode + Zillow API search using the given HTTP client."""
        # Step 1: Geocode to get map bounds (required by the API).
        # Nominatim enforces a 1 req/s policy, so we serialize geocode calls.
        async with self._geocode_lock:
            map_bounds = await _geocode_location(location, http)
        if not map_bounds:
            logger.error(
                "Could not geocode '%s' — API requires mapBounds", location
            )
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
            logger.error(
                "Zillow API HTTP error: %s — body: %s",
                e,
                e.response.text[:500],
            )
            raise ZillowAPIError(
                f"Zillow API returned {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            logger.error("Zillow API request error: %s", e)
            raise ZillowAPIError(f"Zillow API request failed: {e}") from e

        results = data.get("results", [])
        total = data.get("totalCount", "?")
        logger.info(
            "Zillow API returned %d results (totalCount=%s) for '%s'",
            len(results),
            total,
            location,
        )
        return results
