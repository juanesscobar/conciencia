"""Scrapers package"""

from .base import BaseScraper, SCRAPERS, get_scraper, get_all_scrapers, run_all_scrapers, register_scraper
from .remotive import RemotiveScraper
from .wework import WeWorkRemotelyScraper
from .remoteok import RemoteOKScraper
from .appen import AppenScraper

__all__ = [
    "BaseScraper",
    "SCRAPERS", 
    "get_scraper",
    "get_all_scrapers",
    "run_all_scrapers",
    "register_scraper",
    "RemotiveScraper",
    "WeWorkRemotelyScraper",
    "RemoteOKScraper",
    "AppenScraper",
]
