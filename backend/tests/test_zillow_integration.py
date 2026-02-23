"""Integration tests for the Zillow RapidAPI client.

These tests hit the real API and require a valid RAPIDAPI_KEY in the .env file.
Run with:  pytest tests/test_zillow_integration.py -v -s
"""

from __future__ import annotations

import os
import sys

import pytest

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.zillow_client import (  # noqa: E402
    ZillowAPIError,
    ZillowClient,
    _geocode_location,
    _location_to_zillow_slug,
    build_zillow_search_url,
)
from app.services.search_service import _map_zillow_prop_to_listing, _parse_int_from_string  # noqa: E402


# ---------------------------------------------------------------------------
# Unit tests for helpers (always run, no API key needed)
# ---------------------------------------------------------------------------

class TestLocationSlug:
    def test_simple_city_state(self):
        assert _location_to_zillow_slug("New York, NY") == "new-york-ny"

    def test_city_with_periods(self):
        assert _location_to_zillow_slug("Washington D.C.") == "washington-dc"

    def test_multi_word_city(self):
        assert _location_to_zillow_slug("San Francisco, CA") == "san-francisco-ca"

    def test_extra_spaces(self):
        assert _location_to_zillow_slug("  Chicago ,  IL  ") == "chicago-il"

    def test_single_word(self):
        assert _location_to_zillow_slug("Miami") == "miami"


class TestBuildZillowSearchUrl:
    BOUNDS = {"north": 40.92, "south": 40.48, "east": -73.70, "west": -74.26}

    def test_basic_url(self):
        url = build_zillow_search_url("New York, NY", map_bounds=self.BOUNDS)
        assert url.startswith("https://www.zillow.com/new-york-ny/")
        assert "searchQueryState=" in url
        assert "usersSearchTerm" in url
        assert "mapBounds" in url

    def test_url_with_filters(self):
        url = build_zillow_search_url(
            "Chicago, IL",
            map_bounds=self.BOUNDS,
            max_price=500000,
            beds_min=3,
            baths_min=2,
            sqft_min=1500,
        )
        assert "chicago-il" in url
        assert "searchQueryState=" in url
        assert "price" in url
        assert "beds" in url
        assert "baths" in url
        assert "sqft" in url

    def test_url_without_bounds(self):
        url = build_zillow_search_url("New York, NY")
        assert "searchQueryState=" in url
        assert "mapBounds" not in url


class TestParseIntFromString:
    def test_none(self):
        assert _parse_int_from_string(None) is None

    def test_integer(self):
        assert _parse_int_from_string(1500) == 1500

    def test_float(self):
        assert _parse_int_from_string(1500.5) == 1500

    def test_sqft_string(self):
        assert _parse_int_from_string("1,010 sqft") == 1010

    def test_days_string(self):
        assert _parse_int_from_string("1 day") == 1

    def test_large_number(self):
        assert _parse_int_from_string("2,500 sqft") == 2500

    def test_no_number(self):
        assert _parse_int_from_string("N/A") is None


class TestMapZillowPropToListing:
    """Test the mapping from Zillow API response to Listing ORM object."""

    SAMPLE_PROP = {
        "id": "2058616222",
        "price": "$175,000",
        "unformattedPrice": 175000,
        "address": {
            "street": "9222 S Harvard Ave",
            "city": "Chicago",
            "state": "IL",
            "zipcode": "60620",
        },
        "beds": 3,
        "baths": 1,
        "livingArea": "1,010 sqft",
        "imgSrc": "https://photos.zillowstatic.com/example.jpg",
        "detailUrl": "/homedetails/9222-S-Harvard-Ave-Chicago-IL-60620/2058616222_zpid/",
        "daysOnZillow": "1 day",
        "homeType": "SINGLE_FAMILY",
        "latLong": {"latitude": 41.724247, "longitude": -87.632316},
    }

    def test_address_parsing(self):
        listing = _map_zillow_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert "9222 S Harvard Ave" in listing.address
        assert "Chicago" in listing.address
        assert "IL" in listing.address

    def test_price(self):
        listing = _map_zillow_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert listing.price == 175000

    def test_beds_baths(self):
        listing = _map_zillow_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert listing.bedrooms == 3
        assert listing.bathrooms == 1.0

    def test_sqft(self):
        listing = _map_zillow_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert listing.sqft == 1010

    def test_image_url(self):
        listing = _map_zillow_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert listing.image_url == "https://photos.zillowstatic.com/example.jpg"

    def test_zillow_url_relative(self):
        listing = _map_zillow_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert listing.zillow_url.startswith("https://www.zillow.com/homedetails/")

    def test_days_on_market(self):
        listing = _map_zillow_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert listing.days_on_market == 1

    def test_home_type(self):
        listing = _map_zillow_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert listing.property_type == "single family"

    def test_coordinates(self):
        listing = _map_zillow_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert listing.latitude == pytest.approx(41.724247)
        assert listing.longitude == pytest.approx(-87.632316)

    def test_external_id(self):
        listing = _map_zillow_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert listing.external_id == "2058616222"

    def test_neighborhood(self):
        listing = _map_zillow_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert listing.neighborhood == "Chicago"


# ---------------------------------------------------------------------------
# Integration tests — require RAPIDAPI_KEY to be set
# ---------------------------------------------------------------------------

def _has_api_key() -> bool:
    from app.config import settings
    return bool(settings.rapidapi_key)


requires_api_key = pytest.mark.skipif(
    not _has_api_key(),
    reason="RAPIDAPI_KEY not set — skipping live API tests",
)


@requires_api_key
class TestGeocode:
    """Verify Nominatim geocoding works for common locations."""

    @pytest.mark.asyncio
    async def test_geocode_new_york(self):
        import httpx
        async with httpx.AsyncClient() as client:
            bounds = await _geocode_location("New York, NY", client)
        assert bounds is not None
        assert bounds["north"] > bounds["south"]
        assert bounds["east"] > bounds["west"]
        # NYC should be roughly around 40.7 lat, -74 lon
        assert 40.0 < bounds["north"] < 42.0
        assert -75.0 < bounds["west"] < -73.0

    @pytest.mark.asyncio
    async def test_geocode_chicago(self):
        import httpx
        async with httpx.AsyncClient() as client:
            bounds = await _geocode_location("Chicago, IL", client)
        assert bounds is not None
        assert bounds["north"] > bounds["south"]

    @pytest.mark.asyncio
    async def test_geocode_nonsense(self):
        import httpx
        async with httpx.AsyncClient() as client:
            bounds = await _geocode_location("xyznonexistentplace12345", client)
        assert bounds is None


@requires_api_key
class TestZillowClientIntegration:
    """Live API tests — these make real HTTP calls and cost API credits."""

    @pytest.mark.asyncio
    async def test_search_new_york(self):
        """Basic search for New York should return results."""
        client = ZillowClient()
        results = await client.search_by_url("New York, NY")
        assert isinstance(results, list)
        assert len(results) > 0, "Expected at least 1 result for New York, NY"

        # Verify response structure of first result
        first = results[0]
        assert "id" in first or "zpid" in first, f"Missing id field: {first.keys()}"
        assert "address" in first, f"Missing address field: {first.keys()}"

    @pytest.mark.asyncio
    async def test_search_with_price_filter(self):
        """Search with a max price should return results."""
        client = ZillowClient()
        results = await client.search_by_url(
            "Chicago, IL",
            max_price=300000,
        )
        assert isinstance(results, list)
        assert len(results) > 0, "Expected results for Chicago under $300k"

    @pytest.mark.asyncio
    async def test_search_with_beds_filter(self):
        """Search with bed minimum should return results."""
        client = ZillowClient()
        results = await client.search_by_url(
            "Los Angeles, CA",
            beds_min=3,
        )
        assert isinstance(results, list)
        assert len(results) > 0, "Expected results for LA with 3+ beds"

    @pytest.mark.asyncio
    async def test_search_with_all_filters(self):
        """Search with multiple filters combined."""
        client = ZillowClient()
        results = await client.search_by_url(
            "Miami, FL",
            max_price=500000,
            beds_min=2,
            baths_min=2,
        )
        assert isinstance(results, list)
        assert len(results) > 0, "Expected results for Miami with filters"

    @pytest.mark.asyncio
    async def test_result_has_expected_fields(self):
        """Verify the response contains the fields we need for mapping."""
        client = ZillowClient()
        results = await client.search_by_url("New York, NY")
        assert len(results) > 0

        prop = results[0]
        expected_keys = {"address", "detailUrl", "imgSrc"}
        actual_keys = set(prop.keys())
        missing = expected_keys - actual_keys
        assert not missing, f"Missing expected keys: {missing}. Got: {sorted(actual_keys)}"

    @pytest.mark.asyncio
    async def test_full_mapping_with_live_data(self):
        """Fetch live data and verify it maps to a Listing without errors."""
        client = ZillowClient()
        results = await client.search_by_url("New York, NY")
        assert len(results) > 0

        listing = _map_zillow_prop_to_listing(results[0], pipeline_run_id=None, requirement_id=1)
        assert listing.address, "Address should not be empty"
        assert listing.external_id, "External ID should not be empty"

    @pytest.mark.asyncio
    async def test_page_2(self):
        """Pagination should work."""
        client = ZillowClient()
        results = await client.search_by_url("New York, NY", page=2)
        assert isinstance(results, list)
        # Page 2 may or may not have results, but shouldn't error
