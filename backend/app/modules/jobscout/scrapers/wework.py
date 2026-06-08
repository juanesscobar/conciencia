"""We Work Remotely scraper - HTML scraping"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import re

import aiohttp
from bs4 import BeautifulSoup

from ..models import Opportunity
from ..scoring import classify_opportunity, calculate_score
from .base import BaseScraper, register_scraper


@register_scraper
class WeWorkRemotelyScraper(BaseScraper):
    """Scraper for WeWorkRemotely.com (HTML scraping)"""
    
    name = "weworkremotely"
    source = "weworkremotely"
    source_type = "html_scraping"
    rate_limit_delay = 2.0  # Be polite
    
    BASE_URL = "https://weworkremotely.com"
    JOBS_URL = "https://weworkremotely.com/remote-jobs/search?term=developer"
    
    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch jobs from We Work Remotely"""
        await self._rate_limit()
        
        jobs = []
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                async with session.get(self.JOBS_URL, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Find job listings
                        job_listings = soup.find_all('li', class_='feature')
                        
                        for listing in job_listings:
                            try:
                                job = self._parse_listing(listing)
                                if job:
                                    jobs.append(job)
                            except Exception as e:
                                continue
                    else:
                        print(f"[WeWorkRemotely] Error {response.status}")
        except Exception as e:
            print(f"[WeWorkRemotely] Fetch error: {e}")
        
        return jobs
    
    def _parse_listing(self, listing) -> Optional[Dict[str, Any]]:
        """Parse a single job listing"""
        try:
            # Get link
            link_elem = listing.find('a')
            if not link_elem:
                return None
            
            href = link_elem.get('href', '')
            if not href.startswith('/'):
                href = '/' + href
            url = f"{self.BASE_URL}{href}"
            
            # Extract job ID from URL
            job_id = href.split('/')[-1] if '/' in href else href
            
            # Get company and title
            company_elem = listing.find('span', class_='company')
            title_elem = listing.find('span', class_='title')
            
            company = company_elem.text.strip() if company_elem else "Unknown"
            title = title_elem.text.strip() if title_elem else "Unknown"
            
            # Get tags/region
            region_elem = listing.find('span', class_='region')
            region = region_elem.text.strip() if region_elem else "Worldwide"
            
            return {
                "id": f"wwr_{job_id}",
                "title": title,
                "company": company,
                "url": url,
                "region": region,
                "source_url": url
            }
            
        except Exception as e:
            return None
    
    def parse(self, raw_data: Dict[str, Any]) -> Optional[Opportunity]:
        """Parse into Opportunity model"""
        try:
            title = raw_data.get("title", "")
            company = raw_data.get("company", "")
            
            # Classify
            opp_type, app_type, difficulty = classify_opportunity(title, "", company, raw_data.get("url", ""))
            
            # Determine location restrictions
            region = raw_data.get("region", "Worldwide")
            location_restrictions = [region]
            
            opp = Opportunity(
                source=self.source,
                source_id=raw_data["id"],
                title=title,
                company=company,
                description=None,  # Would need to fetch detail page
                url=raw_data["url"],
                location_type="remote",
                location_restrictions=location_restrictions,
                salary_text="Not specified",
                tags=["remote"],
                type=opp_type,
                application_type=app_type,
                difficulty=difficulty,
                raw_data=raw_data
            )
            
            opp.score = calculate_score(opp)
            return opp
            
        except Exception as e:
            print(f"[WeWorkRemotely] Parse error: {e}")
            return None
