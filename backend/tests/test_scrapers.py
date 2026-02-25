"""Unit tests for the multi-source scraper architecture.

Tests cover:
- BaseScraper interface contract
- ScraperRegistry discovery and instantiation
- Each scraper's response mapping (via mock HTTP responses)
- Generic property-to-listing mapping
- Slug / URL helpers for each scraper
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.scrapers.base_scraper import BaseScraper, ScraperError
from app.services.scrapers.registry import ScraperRegistry
from app.services.scrapers.housesigma_scraper import (
    HouseSigmaScraper,
    _location_to_slug as housesigma_slug,
)
from app.services.scrapers.realtor_ca_scraper import RealtorCaScraper
from app.services.scrapers.zoocasa_scraper import ZoocasaScraper
from app.services.scrapers.condos_ca_scraper import CondosCaScraper
from app.services.scrapers.property_ca_scraper import PropertyCaScraper
from app.services.scrapers.zillow_scraper import ZillowScraper
from app.services.scrapers.utils import slugify, canadian_city_slug
from app.services.search_service import (
    _map_generic_prop_to_listing,
    _parse_int_from_string,
)


# ---------------------------------------------------------------------------
# BaseScraper contract tests
# ---------------------------------------------------------------------------

class TestBaseScraper:
    def test_cannot_instantiate_without_source_name(self):
        """A scraper with empty SOURCE_NAME should raise ValueError."""
        class BadScraper(BaseScraper):
            SOURCE_NAME = ""
            async def search(self, location, **kw):
                return []

        with pytest.raises(ValueError, match="must define SOURCE_NAME"):
            BadScraper()

    def test_concrete_scraper_has_source_name(self):
        """All concrete scrapers must have a non-empty SOURCE_NAME."""
        for name, scraper_cls in ScraperRegistry._scrapers.items():
            assert scraper_cls.SOURCE_NAME, f"{name} has empty SOURCE_NAME"


# ---------------------------------------------------------------------------
# ScraperRegistry tests
# ---------------------------------------------------------------------------

class TestScraperRegistry:
    def test_list_sources_returns_all_six(self):
        sources = ScraperRegistry.list_sources()
        expected = {"Zillow", "HouseSigma", "Realtor.ca", "Zoocasa", "Condos.ca", "Property.ca"}
        assert set(sources) == expected

    def test_get_scraper_valid(self):
        # Non-Zillow scrapers don't need API keys
        scraper = ScraperRegistry.get_scraper("HouseSigma")
        assert isinstance(scraper, HouseSigmaScraper)
        assert scraper.SOURCE_NAME == "HouseSigma"

    def test_get_scraper_invalid(self):
        with pytest.raises(ValueError, match="Unknown scraper source"):
            ScraperRegistry.get_scraper("FakeSite")

    def test_get_all_scrapers_skips_failures(self):
        """get_all_scrapers should skip scrapers that fail to init (e.g., missing API key)."""
        scrapers = ScraperRegistry.get_all_scrapers()
        # At minimum, the 5 non-Zillow scrapers should init (no API key needed)
        names = [name for name, _ in scrapers]
        assert "HouseSigma" in names
        assert "Realtor.ca" in names
        assert "Zoocasa" in names
        assert "Condos.ca" in names
        assert "Property.ca" in names

    def test_register_scraper(self):
        """Custom scrapers can be registered."""
        class CustomScraper(BaseScraper):
            SOURCE_NAME = "Custom"
            async def search(self, location, **kw):
                return []

        ScraperRegistry.register_scraper("Custom", CustomScraper)
        assert "Custom" in ScraperRegistry.list_sources()
        scraper = ScraperRegistry.get_scraper("Custom")
        assert isinstance(scraper, CustomScraper)

        # Clean up -- restore default scrapers
        ScraperRegistry.reset()

    def test_register_non_scraper_raises(self):
        with pytest.raises(TypeError, match="must be a subclass"):
            ScraperRegistry.register_scraper("Bad", dict)  # type: ignore


# ---------------------------------------------------------------------------
# Slug / URL helper tests
# ---------------------------------------------------------------------------

class TestHouseSigmaSlug:
    def test_toronto_on(self):
        assert housesigma_slug("Toronto, ON") == "toronto"

    def test_toronto_ontario(self):
        assert housesigma_slug("Toronto, Ontario") == "toronto"

    def test_richmond_hill(self):
        assert housesigma_slug("Richmond Hill, ON") == "richmond-hill"

    def test_vancouver_bc(self):
        assert housesigma_slug("Vancouver, BC") == "vancouver"

    def test_unknown_city(self):
        assert housesigma_slug("Kitchener, ON") == "kitchener"


class TestZoocasaSlug:
    """Zoocasa uses the generic slugify (keeps province in slug)."""

    def test_toronto_on(self):
        assert slugify("Toronto, ON") == "toronto-on"

    def test_vancouver_bc(self):
        assert slugify("Vancouver, BC") == "vancouver-bc"

    def test_extra_spaces(self):
        assert slugify("  Ottawa ,  ON  ") == "ottawa-on"


class TestCondosCaSlug:
    """Condos.ca uses canadian_city_slug (strips province)."""

    def test_toronto_on(self):
        assert canadian_city_slug("Toronto, ON") == "toronto"

    def test_vancouver_bc(self):
        assert canadian_city_slug("Vancouver, BC") == "vancouver"


class TestPropertyCaSlug:
    """Property.ca uses canadian_city_slug (strips province)."""

    def test_toronto_on(self):
        assert canadian_city_slug("Toronto, ON") == "toronto"

    def test_richmond_hill(self):
        assert canadian_city_slug("Richmond Hill, ON") == "richmond-hill"


# ---------------------------------------------------------------------------
# Generic property-to-listing mapping tests
# ---------------------------------------------------------------------------

class TestMapGenericPropToListing:
    SAMPLE_PROP = {
        "id": "MLS12345",
        "source": "Realtor.ca",
        "address": "100 King St W, Toronto, ON",
        "price": 750000,
        "bedrooms": 2,
        "bathrooms": 1.5,
        "sqft": 900,
        "property_type": "condo",
        "description": "Beautiful downtown condo.",
        "image_url": "https://example.com/photo.jpg",
        "listing_url": "https://www.realtor.ca/real-estate/MLS12345",
        "latitude": 43.6489,
        "longitude": -79.3835,
        "neighborhood": "Financial District",
        "days_on_market": 5,
        "year_built": 2018,
    }

    def test_basic_mapping(self):
        listing = _map_generic_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=2)
        assert listing.external_id == "MLS12345"
        assert listing.source == "Realtor.ca"
        assert listing.address == "100 King St W, Toronto, ON"
        assert listing.price == 750000
        assert listing.bedrooms == 2
        assert listing.bathrooms == 1.5
        assert listing.sqft == 900
        assert listing.property_type == "condo"
        assert listing.listing_url == "https://www.realtor.ca/real-estate/MLS12345"
        assert listing.neighborhood == "Financial District"
        assert listing.days_on_market == 5
        assert listing.year_built == 2018

    def test_string_price(self):
        prop = {**self.SAMPLE_PROP, "price": "$1,200,000"}
        listing = _map_generic_prop_to_listing(prop, pipeline_run_id=1, requirement_id=1)
        assert listing.price == 1200000.0

    def test_none_fields(self):
        prop = {
            "id": "X1",
            "source": "Test",
            "address": "",
            "price": None,
            "bedrooms": None,
            "bathrooms": None,
        }
        listing = _map_generic_prop_to_listing(prop, pipeline_run_id=None, requirement_id=1)
        assert listing.price is None
        assert listing.bedrooms is None
        assert listing.bathrooms is None

    def test_data_json_stored(self):
        listing = _map_generic_prop_to_listing(self.SAMPLE_PROP, pipeline_run_id=1, requirement_id=1)
        assert listing.data_json is not None
        parsed = json.loads(listing.data_json)
        assert parsed["id"] == "MLS12345"


# ---------------------------------------------------------------------------
# HouseSigma scraper response parsing tests
# ---------------------------------------------------------------------------

class TestHouseSigmaResponseParsing:
    """Test that HouseSigmaScraper correctly parses API responses."""

    MOCK_API_RESPONSE = {
        "data": {
            "list": [
                {
                    "id_listing": "HS123",
                    "address": "50 Bloor St W",
                    "municipality": "Toronto",
                    "province": "ON",
                    "price": 599000,
                    "bedroom": 2,
                    "bathroom": 1,
                    "sqft": 800,
                    "type_name": "Condo",
                    "description": "Modern condo in Yorkville.",
                    "photo_url": "https://housesigma.com/photos/hs123.jpg",
                    "lat": 43.6700,
                    "lng": -79.3900,
                    "dom": 10,
                },
            ]
        }
    }

    @pytest.mark.asyncio
    async def test_parse_housesigma_response(self):
        scraper = HouseSigmaScraper()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = self.MOCK_API_RESPONSE

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            results = await scraper.search("Toronto, ON")

        assert len(results) == 1
        prop = results[0]
        assert prop["id"] == "HS123"
        assert prop["source"] == "HouseSigma"
        assert "50 Bloor St W" in prop["address"]
        assert "Toronto" in prop["address"]
        assert prop["price"] == 599000
        assert prop["bedrooms"] == 2
        assert prop["bathrooms"] == 1
        assert prop["listing_url"] == "https://housesigma.com/listing/HS123"


# ---------------------------------------------------------------------------
# Realtor.ca scraper response parsing tests
# ---------------------------------------------------------------------------

class TestRealtorCaResponseParsing:
    """Test that RealtorCaScraper correctly parses API responses."""

    MOCK_API_RESPONSE = {
        "Results": [
            {
                "MlsNumber": "C1234567",
                "Property": {
                    "Price": "$899,000",
                    "Address": {
                        "AddressText": "200 University Ave, Toronto, ON",
                        "Latitude": "43.6510",
                        "Longitude": "-79.3840",
                        "CommunityName": "Downtown",
                    },
                    "Photo": [
                        {"HighResPath": "https://cdn.realtor.ca/photo1.jpg"}
                    ],
                    "PublicRemarks": "Stunning downtown condo.",
                },
                "Building": {
                    "Bedrooms": "3",
                    "BathroomTotal": "2",
                    "SizeInterior": "1200",
                    "Type": "Apartment",
                },
            }
        ]
    }

    MOCK_GEOCODE_RESPONSE = [
        {
            "lat": "43.6510",
            "lon": "-79.3840",
            "boundingbox": ["43.60", "43.70", "-79.45", "-79.30"],
        }
    ]

    @pytest.mark.asyncio
    async def test_parse_realtor_ca_response(self):
        scraper = RealtorCaScraper()

        mock_geo_response = MagicMock()
        mock_geo_response.status_code = 200
        mock_geo_response.raise_for_status = MagicMock()
        mock_geo_response.json.return_value = self.MOCK_GEOCODE_RESPONSE

        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.raise_for_status = MagicMock()
        mock_search_response.json.return_value = self.MOCK_API_RESPONSE

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            # First call is geocode (GET), second is search (POST)
            mock_client.get = AsyncMock(return_value=mock_geo_response)
            mock_client.post = AsyncMock(return_value=mock_search_response)
            mock_client_cls.return_value = mock_client

            results = await scraper.search("Toronto, ON")

        assert len(results) == 1
        prop = results[0]
        assert prop["id"] == "C1234567"
        assert prop["source"] == "Realtor.ca"
        assert "200 University Ave" in prop["address"]
        assert prop["price"] == 899000.0
        assert prop["bedrooms"] == 3
        assert prop["bathrooms"] == 2.0
        assert prop["listing_url"] == "https://www.realtor.ca/real-estate/C1234567"


# ---------------------------------------------------------------------------
# Zoocasa scraper response parsing tests
# ---------------------------------------------------------------------------

class TestZoocasaResponseParsing:
    MOCK_API_RESPONSE = {
        "listings": [
            {
                "mlsNumber": "Z9876",
                "address": {
                    "street": "300 Front St W",
                    "city": "Toronto",
                    "province": "ON",
                    "postalCode": "M5V 3A6",
                },
                "price": 650000,
                "bedrooms": 1,
                "bathrooms": 1,
                "sqft": 550,
                "propertyType": "Condo",
                "description": "Waterfront condo.",
                "imageUrl": "https://zoocasa.com/photos/z9876.jpg",
                "slug": "toronto/300-front-st-w",
                "latitude": 43.6420,
                "longitude": -79.3870,
                "daysOnMarket": 3,
            }
        ]
    }

    @pytest.mark.asyncio
    async def test_parse_zoocasa_response(self):
        scraper = ZoocasaScraper()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = self.MOCK_API_RESPONSE

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            results = await scraper.search("Toronto, ON")

        assert len(results) == 1
        prop = results[0]
        assert prop["id"] == "Z9876"
        assert prop["source"] == "Zoocasa"
        assert "300 Front St W" in prop["address"]
        assert prop["price"] == 650000
        assert prop["listing_url"] == "https://www.zoocasa.com/toronto/300-front-st-w"


# ---------------------------------------------------------------------------
# Condos.ca scraper response parsing tests
# ---------------------------------------------------------------------------

class TestCondosCaResponseParsing:
    MOCK_API_RESPONSE = {
        "listings": [
            {
                "mlsNumber": "CC5555",
                "address": {
                    "street": "1 Yonge St",
                    "city": "Toronto",
                    "province": "ON",
                },
                "price": 1200000,
                "bedrooms": 3,
                "bathrooms": 2,
                "sqft": 1400,
                "propertyType": "condo",
                "description": "Luxury waterfront condo.",
                "imageUrl": "https://condos.ca/photos/cc5555.jpg",
                "slug": "toronto/1-yonge-st",
                "latitude": 43.6400,
                "longitude": -79.3770,
                "daysOnMarket": 14,
            }
        ]
    }

    @pytest.mark.asyncio
    async def test_parse_condos_ca_response(self):
        scraper = CondosCaScraper()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = self.MOCK_API_RESPONSE

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            results = await scraper.search("Toronto, ON")

        assert len(results) == 1
        prop = results[0]
        assert prop["id"] == "CC5555"
        assert prop["source"] == "Condos.ca"
        assert "1 Yonge St" in prop["address"]
        assert prop["price"] == 1200000
        assert prop["listing_url"] == "https://condos.ca/toronto/1-yonge-st"


# ---------------------------------------------------------------------------
# Property.ca scraper response parsing tests
# ---------------------------------------------------------------------------

class TestPropertyCaResponseParsing:
    MOCK_API_RESPONSE = {
        "listings": [
            {
                "mlsNumber": "PC7777",
                "address": {
                    "street": "55 Harbour Sq",
                    "city": "Toronto",
                    "province": "ON",
                    "neighborhood": "Harbourfront",
                },
                "price": 480000,
                "bedrooms": 1,
                "bathrooms": 1,
                "sqft": 600,
                "propertyType": "Condo",
                "description": "Lakefront living.",
                "imageUrl": "https://property.ca/photos/pc7777.jpg",
                "slug": "toronto/55-harbour-sq",
                "latitude": 43.6380,
                "longitude": -79.3760,
                "daysOnMarket": 7,
                "yearBuilt": 1986,
            }
        ]
    }

    @pytest.mark.asyncio
    async def test_parse_property_ca_response(self):
        scraper = PropertyCaScraper()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = self.MOCK_API_RESPONSE

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            results = await scraper.search("Toronto, ON")

        assert len(results) == 1
        prop = results[0]
        assert prop["id"] == "PC7777"
        assert prop["source"] == "Property.ca"
        assert "55 Harbour Sq" in prop["address"]
        assert prop["price"] == 480000
        assert prop["listing_url"] == "https://www.property.ca/toronto/55-harbour-sq"
        assert prop["year_built"] == 1986
        assert prop["neighborhood"] == "Harbourfront"


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestScraperErrorHandling:
    """Verify scrapers raise ScraperError on HTTP failures."""

    @pytest.mark.asyncio
    async def test_housesigma_http_error(self):
        scraper = HouseSigmaScraper()

        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(ScraperError, match="HouseSigma returned 403"):
                await scraper.search("Toronto, ON")

    @pytest.mark.asyncio
    async def test_zoocasa_http_error(self):
        scraper = ZoocasaScraper()

        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(ScraperError, match="Zoocasa returned 500"):
                await scraper.search("Toronto, ON")

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_list(self):
        """Scrapers should return [] when API returns no results."""
        scraper = CondosCaScraper()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"listings": []}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            results = await scraper.search("Toronto, ON")

        assert results == []
