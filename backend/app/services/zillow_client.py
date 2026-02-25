"""
Zillow RapidAPI client for property search via real-estate101.

DEPRECATED: This module is maintained for backward compatibility.
New code should use app.services.scrapers.zillow_scraper instead.
"""

from __future__ import annotations

# Re-export from the new scraper module for backward compatibility
from app.services.scrapers.zillow_scraper import (
    ZillowScraper as ZillowClient,
    _geocode_location,
    _location_to_zillow_slug,
    build_zillow_search_url,
)
from app.services.scrapers.base_scraper import ScraperError as ZillowAPIError

__all__ = [
    "ZillowClient",
    "ZillowAPIError",
    "_location_to_zillow_slug",
    "_geocode_location",
    "build_zillow_search_url",
]
