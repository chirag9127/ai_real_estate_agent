"""Registry of available real estate property scrapers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.services.scrapers.base_scraper import BaseScraper, ScraperError
from app.services.scrapers.condos_ca_scraper import CondosCaScraper
from app.services.scrapers.housesigma_scraper import HouseSigmaScraper
from app.services.scrapers.property_ca_scraper import PropertyCaScraper
from app.services.scrapers.realtor_ca_scraper import RealtorCaScraper
from app.services.scrapers.zillow_scraper import ZillowScraper
from app.services.scrapers.zoocasa_scraper import ZoocasaScraper

if TYPE_CHECKING:
    from typing import Type

logger = logging.getLogger(__name__)


class ScraperRegistry:
    """Registry and factory for real estate scrapers."""

    # Map of source names to scraper classes
    _scrapers: dict[str, Type[BaseScraper]] = {
        "Zillow": ZillowScraper,
        "HouseSigma": HouseSigmaScraper,
        "Realtor.ca": RealtorCaScraper,
        "Zoocasa": ZoocasaScraper,
        "Condos.ca": CondosCaScraper,
        "Property.ca": PropertyCaScraper,
    }

    @classmethod
    def get_scraper(cls, source_name: str) -> BaseScraper:
        """
        Get a scraper instance by source name.

        Args:
            source_name: Name of the scraper (e.g., "Zillow", "Realtor.ca")

        Returns:
            An instance of the requested scraper.

        Raises:
            ValueError: If the source name is not registered.
        """
        scraper_class = cls._scrapers.get(source_name)
        if not scraper_class:
            raise ValueError(
                f"Unknown scraper source: {source_name}. "
                f"Available: {', '.join(cls._scrapers.keys())}"
            )
        return scraper_class()

    @classmethod
    def get_all_scrapers(cls) -> list[tuple[str, BaseScraper]]:
        """
        Get instances of all registered scrapers that can be initialized.

        Returns a list of (name, scraper) tuples, skipping scrapers that
        fail to initialize (e.g., missing API keys).
        """
        scrapers: list[tuple[str, BaseScraper]] = []
        for name, scraper_class in cls._scrapers.items():
            try:
                scrapers.append((name, scraper_class()))
            except (ScraperError, Exception) as e:
                logger.warning(
                    "Skipping scraper %s: initialization failed: %s",
                    name, e,
                )
        return scrapers

    @classmethod
    def list_sources(cls) -> list[str]:
        """List all available scraper source names."""
        return list(cls._scrapers.keys())

    @classmethod
    def register_scraper(
        cls, source_name: str, scraper_class: Type[BaseScraper]
    ) -> None:
        """Register a new scraper class."""
        if not issubclass(scraper_class, BaseScraper):
            raise TypeError(
                f"{scraper_class.__name__} must be a subclass of BaseScraper"
            )
        cls._scrapers[source_name] = scraper_class
        logger.info(
            "Registered scraper: %s -> %s", source_name, scraper_class.__name__
        )
