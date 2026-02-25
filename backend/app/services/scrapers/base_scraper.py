"""Base class for real estate property scrapers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base exception for scraper errors."""

    pass


class BaseScraper(ABC):
    """Abstract base class for real estate property scrapers."""

    # Subclasses must define this
    SOURCE_NAME: str = ""

    def __init__(self) -> None:
        """Initialize the scraper."""
        if not self.SOURCE_NAME:
            raise ValueError(f"{self.__class__.__name__} must define SOURCE_NAME")

    @abstractmethod
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
        Search for properties in the given location with optional filters.

        Args:
            location: City, state, or region to search (e.g., "New York, NY")
            max_price: Maximum price filter
            beds_min: Minimum number of bedrooms
            baths_min: Minimum number of bathrooms
            sqft_min: Minimum square footage
            **kwargs: Additional scraper-specific parameters

        Returns:
            List of property dicts with keys:
            - id: Unique property ID (source-specific)
            - address: Full address
            - price: Numeric price
            - bedrooms: Number of bedrooms
            - bathrooms: Number of bathrooms
            - sqft: Square footage (optional)
            - property_type: Type of property (e.g., "house", "condo")
            - description: Property description (optional)
            - image_url: Primary image URL (optional)
            - listing_url: Direct URL to listing on source site
            - And any other fields the scraper can extract
        """
        pass

    async def search_with_pagination(
        self,
        location: str,
        *,
        max_price: int | None = None,
        beds_min: int | None = None,
        baths_min: int | None = None,
        sqft_min: int | None = None,
        max_results: int = 100,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        Search with automatic pagination, gathering up to max_results properties.

        Default implementation calls search() once.
        Subclasses can override for multi-page scraping.
        """
        results = await self.search(
            location,
            max_price=max_price,
            beds_min=beds_min,
            baths_min=baths_min,
            sqft_min=sqft_min,
            **kwargs,
        )
        return results[:max_results]
