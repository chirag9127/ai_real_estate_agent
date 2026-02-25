"""Realtor.ca scraper for Canadian real estate data.

Realtor.ca is Canada's primary real estate search platform operated by CREA
(Canadian Real Estate Association). This scraper uses their public-facing
property search API endpoint.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.scrapers.base_scraper import BaseScraper, ScraperError
from app.services.scrapers.utils import build_browser_headers, nominatim_lock

logger = logging.getLogger(__name__)

# Realtor.ca property search API (used by their web frontend)
_REALTOR_CA_API_URL = "https://api2.realtor.ca/Listing.svc/PropertySearch_Post"

_HEADERS = build_browser_headers(
    origin="https://www.realtor.ca",
    referer="https://www.realtor.ca/",
)

# Nominatim for geocoding locations to lat/lng
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_NOMINATIM_HEADERS = {"User-Agent": "AIRealEstateAgent/1.0"}


async def _geocode_for_realtor(
    location: str,
    http_client: httpx.AsyncClient,
) -> dict[str, float] | None:
    """Geocode a location to lat/lng for Realtor.ca search."""
    try:
        async with nominatim_lock:
            response = await http_client.get(
                _NOMINATIM_URL,
                params={
                    "q": location,
                    "format": "json",
                    "limit": "1",
                    "countrycodes": "ca",
                },
                headers=_NOMINATIM_HEADERS,
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

    result = data[0]
    lat = float(result.get("lat", 0))
    lon = float(result.get("lon", 0))
    bbox = result.get("boundingbox", [])

    if not bbox or len(bbox) < 4:
        return {"lat": lat, "lng": lon}

    return {
        "lat": lat,
        "lng": lon,
        "lat_min": float(bbox[0]),
        "lat_max": float(bbox[1]),
        "lng_min": float(bbox[2]),
        "lng_max": float(bbox[3]),
    }


class RealtorCaScraper(BaseScraper):
    """Realtor.ca property scraper for Canadian real estate."""

    SOURCE_NAME = "Realtor.ca"

    def __init__(self, timeout: float = 30.0) -> None:
        super().__init__()
        self._timeout = timeout

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
        Search Realtor.ca for properties via their PropertySearch API.

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
            "Searching Realtor.ca: location=%s, max_price=%s, beds=%s, baths=%s",
            location, max_price, beds_min, baths_min,
        )

        async with httpx.AsyncClient(
            timeout=self._timeout,
            headers=_HEADERS,
        ) as client:
            # Step 1: Geocode the location
            geo = await _geocode_for_realtor(location, client)
            if not geo:
                logger.error(
                    "Could not geocode '%s' for Realtor.ca search", location
                )
                return []

            # Step 2: Build the form data for the POST request
            form_data: dict[str, Any] = {
                "CultureId": "1",
                "ApplicationId": "1",
                "PropertySearchTypeId": "1",  # Residential
                "TransactionTypeId": "2",  # For sale
                "LatitudeMax": geo.get("lat_max", geo["lat"] + 0.1),
                "LatitudeMin": geo.get("lat_min", geo["lat"] - 0.1),
                "LongitudeMax": geo.get("lng_max", geo["lng"] + 0.1),
                "LongitudeMin": geo.get("lng_min", geo["lng"] - 0.1),
                "RecordsPerPage": "50",
                "CurrentPage": str(kwargs.get("page", 1)),
                "SortBy": "1",
                "SortOrder": "A",
            }

            if max_price is not None:
                form_data["PriceMax"] = str(max_price)
            if beds_min is not None:
                form_data["BedRange"] = f"{beds_min}-0"
            if baths_min is not None:
                form_data["BathRange"] = f"{baths_min}-0"

            # Step 3: Make the API request
            try:
                response = await client.post(
                    _REALTOR_CA_API_URL,
                    data=form_data,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.error(
                    "Realtor.ca HTTP error: %s -- %s",
                    e.response.status_code,
                    e.response.text[:200],
                )
                raise ScraperError(
                    f"Realtor.ca returned {e.response.status_code}"
                ) from e
            except httpx.RequestError as e:
                logger.error("Realtor.ca request error: %s", e)
                raise ScraperError(
                    f"Realtor.ca request failed: {e}"
                ) from e

        # Step 4: Parse results
        raw_results = data.get("Results", [])
        if not raw_results:
            logger.warning("Realtor.ca returned no results for '%s'", location)
            return []

        results: list[dict[str, Any]] = []
        for item in raw_results:
            prop = item.get("Property", {})
            building = item.get("Building", {})
            address_obj = prop.get("Address", {})
            photo = (prop.get("Photo", [{}]) or [{}])[0]

            # Build full address
            full_address = address_obj.get("AddressText", "")

            # Build listing URL
            mls_number = item.get("MlsNumber", "")
            listing_url = (
                f"https://www.realtor.ca/real-estate/{mls_number}"
                if mls_number
                else ""
            )

            # Parse price
            price_str = prop.get("Price", "")
            price = None
            if price_str:
                try:
                    price = float(
                        price_str.replace("$", "")
                        .replace(",", "")
                        .strip()
                    )
                except (ValueError, AttributeError):
                    pass

            # Parse beds/baths from Building
            bedrooms = None
            bathrooms = None
            bed_str = building.get("Bedrooms", "")
            bath_str = building.get("BathroomTotal", "")
            if bed_str:
                try:
                    bedrooms = int(bed_str)
                except (ValueError, TypeError):
                    pass
            if bath_str:
                try:
                    bathrooms = float(bath_str)
                except (ValueError, TypeError):
                    pass

            # Square footage
            sqft = None
            size_str = building.get("SizeInterior", "")
            if size_str:
                try:
                    sqft = int(
                        size_str.replace(",", "")
                        .replace(" sqft", "")
                        .strip()
                    )
                except (ValueError, TypeError):
                    pass

            results.append({
                "id": mls_number or str(item.get("Id", "")),
                "source": self.SOURCE_NAME,
                "address": full_address,
                "price": price,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "sqft": sqft,
                "property_type": building.get("Type", ""),
                "description": prop.get("PublicRemarks", ""),
                "image_url": photo.get("HighResPath") or photo.get("MedResPath", ""),
                "listing_url": listing_url,
                "latitude": prop.get("Address", {}).get("Latitude"),
                "longitude": prop.get("Address", {}).get("Longitude"),
                "neighborhood": address_obj.get("CommunityName", ""),
            })

        logger.info(
            "Realtor.ca returned %d results for '%s'",
            len(results), location,
        )
        return results
