"""Real estate property scrapers."""

from app.services.scrapers.base_scraper import BaseScraper, ScraperError
from app.services.scrapers.condos_ca_scraper import CondosCaScraper
from app.services.scrapers.housesigma_scraper import HouseSigmaScraper
from app.services.scrapers.property_ca_scraper import PropertyCaScraper
from app.services.scrapers.realtor_ca_scraper import RealtorCaScraper
from app.services.scrapers.registry import ScraperRegistry
from app.services.scrapers.zillow_scraper import ZillowScraper
from app.services.scrapers.zoocasa_scraper import ZoocasaScraper

__all__ = [
    "BaseScraper",
    "ScraperError",
    "ZillowScraper",
    "HouseSigmaScraper",
    "RealtorCaScraper",
    "ZoocasaScraper",
    "CondosCaScraper",
    "PropertyCaScraper",
    "ScraperRegistry",
]
