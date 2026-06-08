"""Base scraper class and scraper registry"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
import asyncio
import logging

from ..models import Opportunity, ScoutRun

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all job/opportunity scrapers"""
    
    name: str = "base"  # Scraper identifier
    source: str = "base"  # Source name (e.g., "remotive", "wework")
    source_type: str = "api"  # api, rss, html_scraping
    
    # Rate limiting
    rate_limit_delay: float = 1.0  # Seconds between requests
    
    def __init__(self):
        self.last_request_time: Optional[datetime] = None
    
    async def _rate_limit(self):
        """Apply rate limiting between requests"""
        if self.last_request_time:
            elapsed = (datetime.utcnow() - self.last_request_time).total_seconds()
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = datetime.utcnow()
    
    @abstractmethod
    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch raw data from source
        
        Returns list of raw opportunity data from the source.
        Each item should be a dict that parse() can handle.
        """
        pass
    
    @abstractmethod
    def parse(self, raw_data: Dict[str, Any]) -> Optional[Opportunity]:
        """Parse raw data into Opportunity model
        
        Returns Opportunity instance or None if parsing fails.
        """
        pass
    
    async def scout(self) -> tuple[int, int, List[Opportunity]]:
        """Run full scout: fetch + parse + return opportunities
        
        Returns: (total_found, new_opportunities, all_parsed)
        """
        logger.info(f"[{self.name}] Starting scout...")
        
        try:
            raw_items = await self.fetch()
            logger.info(f"[{self.name}] Fetched {len(raw_items)} raw items")
            
            opportunities = []
            for item in raw_items:
                try:
                    opp = self.parse(item)
                    if opp:
                        opportunities.append(opp)
                except Exception as e:
                    logger.warning(f"[{self.name}] Parse error: {e}")
                    continue
            
            logger.info(f"[{self.name}] Parsed {len(opportunities)} opportunities")
            return len(raw_items), len(opportunities), opportunities
            
        except Exception as e:
            logger.error(f"[{self.name}] Scout failed: {e}")
            raise


# Registry of all scrapers
SCRAPERS: Dict[str, BaseScraper] = {}


def register_scraper(scraper_class: type):
    """Decorator to register a scraper"""
    instance = scraper_class()
    SCRAPERS[instance.name] = instance
    return scraper_class


def get_scraper(name: str) -> Optional[BaseScraper]:
    """Get scraper by name"""
    return SCRAPERS.get(name)


def get_all_scrapers() -> Dict[str, BaseScraper]:
    """Get all registered scrapers"""
    return SCRAPERS.copy()


async def run_all_scrapers() -> Dict[str, tuple]:
    """Run all registered scrapers concurrently
    
    Returns: {scraper_name: (total_found, new_opportunities, opportunities)}
    """
    results = {}
    
    async def run_scraper(name: str, scraper: BaseScraper):
        try:
            total, new, opps = await scraper.scout()
            results[name] = (total, new, opps)
        except Exception as e:
            logger.error(f"Scraper {name} failed: {e}")
            results[name] = (0, 0, [])
    
    # Run all scrapers concurrently
    tasks = [
        run_scraper(name, scraper)
        for name, scraper in SCRAPERS.items()
    ]
    
    await asyncio.gather(*tasks, return_exceptions=True)
    
    return results
