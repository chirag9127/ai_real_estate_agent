"""Tests for the parallelized scraper (async context manager, semaphore, gather).

These tests use mocked HTTP responses so they never hit real APIs.
Run with:  pytest tests/test_parallel_search.py -v
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.zillow_client import (
    DEFAULT_MAX_CONCURRENCY,
    ZillowAPIError,
    ZillowClient,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

FAKE_ZILLOW_RESPONSE = {
    "results": [
        {
            "id": "123",
            "address": {"street": "1 Main St", "city": "NY", "state": "NY", "zipcode": "10001"},
            "unformattedPrice": 500000,
            "beds": 2,
            "baths": 1,
        }
    ],
    "totalCount": 1,
}


def _make_mock_response(json_data, status_code=200):
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture()
def _mock_settings():
    """Patch zillow_client.settings with fake API credentials."""
    with patch("app.services.zillow_client.settings") as mock_settings:
        mock_settings.rapidapi_key = "fake-key"
        mock_settings.rapidapi_zillow_host = "fake-host"
        yield mock_settings


# ---------------------------------------------------------------------------
# ZillowClient async context manager tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_mock_settings")
class TestZillowClientContextManager:
    """Verify the async context manager lifecycle."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_shared_client(self):
        """Entering the context manager should create a shared httpx client."""
        client = ZillowClient()
        assert client._shared_http is None

        async with client as ctx:
            assert ctx is client
            assert client._shared_http is not None

        # After exiting, shared client should be cleaned up
        assert client._shared_http is None

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_exception(self):
        """The shared client should be closed even if an exception occurs."""
        client = ZillowClient()
        try:
            async with client:
                assert client._shared_http is not None
                raise RuntimeError("boom")
        except RuntimeError:
            pass

        assert client._shared_http is None


# ---------------------------------------------------------------------------
# Backward compatibility (no context manager)
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_mock_settings")
class TestBackwardCompatibility:
    """Verify that ZillowClient works without the context manager."""

    @pytest.mark.asyncio
    async def test_search_without_context_manager(self):
        """search_by_url should work without entering the context manager."""
        client = ZillowClient()
        assert client._shared_http is None  # no context manager

        with patch("app.services.zillow_client._geocode_location", new_callable=AsyncMock) as mock_geo:
            mock_geo.return_value = {"north": 40.92, "south": 40.48, "east": -73.70, "west": -74.26}

            with patch("httpx.AsyncClient") as MockAsyncClient:
                mock_http = AsyncMock()
                mock_http.get = AsyncMock(return_value=_make_mock_response(FAKE_ZILLOW_RESPONSE))
                # Make it work as both context manager and regular object
                MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_http)
                MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=None)

                results = await client.search_by_url("New York, NY")
                assert len(results) == 1
                assert results[0]["id"] == "123"


# ---------------------------------------------------------------------------
# Semaphore / concurrency control tests
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_mock_settings")
class TestConcurrencyControl:
    """Verify the semaphore limits concurrent requests."""

    @pytest.mark.asyncio
    async def test_default_max_concurrency(self):
        """Default semaphore value should match DEFAULT_MAX_CONCURRENCY."""
        client = ZillowClient()
        assert client._semaphore._value == DEFAULT_MAX_CONCURRENCY

    @pytest.mark.asyncio
    async def test_custom_max_concurrency(self):
        """Custom max_concurrency should be respected."""
        client = ZillowClient(max_concurrency=2)
        assert client._semaphore._value == 2

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Only max_concurrency searches should run at the same time."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        client = ZillowClient(max_concurrency=2)

        async def slow_search(http, location, **kwargs):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)

            await asyncio.sleep(0.05)  # simulate network delay

            async with lock:
                current_concurrent -= 1

            return [{"id": location, "address": location}]

        client._do_search = slow_search

        async with client:
            tasks = [client.search_by_url(f"Location {i}") for i in range(5)]
            results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert max_concurrent <= 2


# ---------------------------------------------------------------------------
# Parallel search via asyncio.gather
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_mock_settings")
class TestParallelSearch:
    """Verify that multiple locations are searched concurrently."""

    @pytest.mark.asyncio
    async def test_parallel_searches_are_faster_than_sequential(self):
        """Concurrent searches should complete faster than sequential."""
        client = ZillowClient(max_concurrency=5)

        async def slow_search(http, location, **kwargs):
            await asyncio.sleep(0.1)  # 100ms per search
            return [{"id": location}]

        client._do_search = slow_search

        async with client:
            start = time.monotonic()
            tasks = [client.search_by_url(f"City {i}") for i in range(5)]
            results = await asyncio.gather(*tasks)
            parallel_time = time.monotonic() - start

        assert len(results) == 5
        # 5 searches × 100ms each = 500ms sequential;
        # parallel should be well under 400ms
        assert parallel_time < 0.4, (
            f"Parallel search took {parallel_time:.3f}s, expected < 0.4s"
        )

    @pytest.mark.asyncio
    async def test_gather_collects_all_results(self):
        """asyncio.gather should collect results from all locations."""
        client = ZillowClient(max_concurrency=5)
        call_order: list[str] = []

        async def tracking_search(http, location, **kwargs):
            call_order.append(location)
            return [{"id": location, "address": location}]

        client._do_search = tracking_search

        locations = ["New York, NY", "Chicago, IL", "Miami, FL"]
        async with client:
            results = await asyncio.gather(
                *(client.search_by_url(loc) for loc in locations)
            )

        assert len(results) == 3
        assert set(call_order) == set(locations)

    @pytest.mark.asyncio
    async def test_partial_failure_does_not_block_others(self):
        """If one location fails, others should still return results."""
        client = ZillowClient(max_concurrency=5)

        async def flaky_search(http, location, **kwargs):
            if location == "Bad Location":
                raise ZillowAPIError("API error for Bad Location")
            return [{"id": location}]

        client._do_search = flaky_search

        async with client:
            async def safe_search(loc):
                try:
                    return await client.search_by_url(loc)
                except ZillowAPIError:
                    return []

            results = await asyncio.gather(
                safe_search("New York, NY"),
                safe_search("Bad Location"),
                safe_search("Chicago, IL"),
            )

        assert len(results) == 3
        assert len(results[0]) == 1  # New York succeeded
        assert len(results[1]) == 0  # Bad Location failed gracefully
        assert len(results[2]) == 1  # Chicago succeeded


# ---------------------------------------------------------------------------
# ZillowClient init validation
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_mock_settings")
class TestZillowClientInit:
    """Verify constructor validation."""

    def test_raises_without_api_key(self):
        with patch("app.services.zillow_client.settings") as mock_settings:
            mock_settings.rapidapi_key = ""
            mock_settings.rapidapi_zillow_host = "fake-host"

            with pytest.raises(ZillowAPIError, match="RAPIDAPI_KEY is not configured"):
                ZillowClient()

    def test_accepts_explicit_api_key(self):
        with patch("app.services.zillow_client.settings") as mock_settings:
            mock_settings.rapidapi_key = ""
            mock_settings.rapidapi_zillow_host = "fake-host"

            client = ZillowClient(api_key="explicit-key")
            assert client._headers["x-rapidapi-key"] == "explicit-key"

    def test_raises_on_invalid_max_concurrency(self):
        """max_concurrency < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="max_concurrency must be >= 1"):
            ZillowClient(max_concurrency=0)


# ---------------------------------------------------------------------------
# Re-entrant context manager guard
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_mock_settings")
class TestReentrantGuard:
    """Verify that nested async-with on the same client is rejected."""

    @pytest.mark.asyncio
    async def test_reentrant_aenter_raises(self):
        """Calling __aenter__ twice without __aexit__ should raise."""
        client = ZillowClient()
        async with client:
            with pytest.raises(RuntimeError, match="not reentrant"):
                await client.__aenter__()


# ---------------------------------------------------------------------------
# Nominatim rate-limit serialization
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("_mock_settings")
class TestNominatimSerialization:
    """Verify that Nominatim geocode calls are serialized via the lock."""

    @pytest.mark.asyncio
    async def test_nominatim_calls_are_serialized(self):
        """Concurrent searches should serialize their geocode calls."""
        geocode_concurrent = 0
        max_geocode_concurrent = 0
        lock = asyncio.Lock()

        client = ZillowClient(max_concurrency=5)

        original_geocode = None  # not needed, we patch at module level

        async def tracking_geocode(location, http_client):
            nonlocal geocode_concurrent, max_geocode_concurrent
            async with lock:
                geocode_concurrent += 1
                max_geocode_concurrent = max(max_geocode_concurrent, geocode_concurrent)

            await asyncio.sleep(0.02)  # simulate geocode latency

            async with lock:
                geocode_concurrent -= 1

            return {"north": 40.92, "south": 40.48, "east": -73.70, "west": -74.26}

        with patch("app.services.zillow_client._geocode_location", side_effect=tracking_geocode):
            # Mock the Zillow API response so _do_search completes
            mock_response = _make_mock_response({"results": [{"id": "1"}], "totalCount": 1})

            async with client:
                # Patch the shared http client's get method
                client._shared_http.get = AsyncMock(return_value=mock_response)

                tasks = [client.search_by_url(f"City {i}") for i in range(5)]
                results = await asyncio.gather(*tasks)

        # All 5 should complete
        assert len(results) == 5
        # Geocode calls should have been serialized (max 1 at a time)
        assert max_geocode_concurrent == 1
