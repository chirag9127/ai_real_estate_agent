"""Unit tests for MLS number extraction from Zillow API response data."""

from __future__ import annotations

import json

from app.services.search_service import _map_zillow_prop_to_listing


def _make_listing(prop: dict) -> object:
    """Helper: map a Zillow property dict to a Listing via the service function."""
    return _map_zillow_prop_to_listing(prop, pipeline_run_id=None, requirement_id=1)


class TestMLSExtraction:
    """Tests for MLS number extraction in _map_zillow_prop_to_listing."""

    def test_mlsid_key(self):
        """MLS number from top-level 'mlsid' key."""
        listing = _make_listing({"mlsid": "MLS-12345", "address": "123 Main St"})
        assert listing.mls_number == "MLS-12345"

    def test_mlsId_key(self):
        """MLS number from top-level 'mlsId' key."""
        listing = _make_listing({"mlsId": "22-04567", "address": "456 Oak Ave"})
        assert listing.mls_number == "22-04567"

    def test_listing_sub_type_mls_id(self):
        """MLS number from listing_sub_type.mls_id."""
        prop = {
            "address": "789 Pine Rd",
            "listing_sub_type": {"mls_id": "SUB-99887"},
        }
        listing = _make_listing(prop)
        assert listing.mls_number == "SUB-99887"

    def test_attribution_info_mlsId(self):
        """MLS number from attributionInfo.mlsId."""
        prop = {
            "address": "321 Elm St",
            "attributionInfo": {"mlsId": "ATTR-55555"},
        }
        listing = _make_listing(prop)
        assert listing.mls_number == "ATTR-55555"

    def test_listingId_key(self):
        """MLS number from top-level 'listingId' key."""
        listing = _make_listing({"listingId": "LID-001", "address": "10 Birch Ln"})
        assert listing.mls_number == "LID-001"

    def test_no_mls_number_available(self):
        """MLS number is None when no relevant key is present."""
        listing = _make_listing({"address": "0 Nowhere Blvd", "zpid": "999"})
        assert listing.mls_number is None

    def test_numeric_mls_id_cast_to_string(self):
        """Numeric MLS IDs are converted to strings."""
        listing = _make_listing({"mlsid": 7654321, "address": "5 Number St"})
        assert listing.mls_number == "7654321"

    def test_priority_order(self):
        """When multiple keys are present, mlsid takes precedence."""
        prop = {
            "mlsid": "FIRST",
            "mlsId": "SECOND",
            "listingId": "THIRD",
            "address": "Priority Lane",
        }
        listing = _make_listing(prop)
        assert listing.mls_number == "FIRST"

    def test_mls_number_stored_alongside_external_id(self):
        """Both mls_number and external_id are independently populated."""
        prop = {"zpid": "12345678", "mlsid": "MLS-ABCDEF", "address": "Both St"}
        listing = _make_listing(prop)
        assert listing.mls_number == "MLS-ABCDEF"
        assert listing.external_id == "12345678"

    def test_full_zillow_response_shape(self):
        """Realistic Zillow response with nested address + MLS info."""
        prop = {
            "id": "zpid-42",
            "address": {"street": "100 Real Ave", "city": "Austin", "state": "TX", "zipcode": "78701"},
            "unformattedPrice": 550000,
            "beds": 3,
            "baths": 2.5,
            "livingArea": "2,100 sqft",
            "homeType": "SINGLE_FAMILY",
            "mlsid": "AUS-2024-001",
            "detailUrl": "/homedetails/100-Real-Ave/42_zpid/",
            "imgSrc": "https://photos.zillow.com/img.jpg",
        }
        listing = _make_listing(prop)
        assert listing.mls_number == "AUS-2024-001"
        assert listing.address == "100 Real Ave, Austin, TX, 78701"
        assert listing.price == 550000
        assert listing.bedrooms == 3
        assert listing.bathrooms == 2.5
        # data_json should contain the full prop
        data = json.loads(listing.data_json)
        assert data["mlsid"] == "AUS-2024-001"
