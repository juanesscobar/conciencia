"""Appen scraper - Microtasks and AI training jobs"""

from datetime import datetime
from typing import List, Dict, Any, Optional

import aiohttp
from bs4 import BeautifulSoup

from ..models import Opportunity, OpportunityType, ApplicationType
from ..scoring import calculate_score
from .base import BaseScraper, register_scraper


@register_scraper
class AppenScraper(BaseScraper):
    """Scraper for Appen.com - Microtask platform
    
    Appen offers various microtasks and longer-term projects for:
    - AI training data labeling
    - Search media evaluation
    - Transcription
    - Translation
    - Survey participation
    """
    
    name = "appen"
    source = "appen"
    source_type = "html_scraping"
    rate_limit_delay = 2.0
    
    # Appen has different job boards by region
    URLS = [
        "https://jobs.appen.com/search/?createNewAlert=false&q=&optionsFacetsDD_country=PY",  # Paraguay
        "https://jobs.appen.com/search/?createNewAlert=false&q=&optionsFacetsDD_country=AR",  # Argentina
        "https://jobs.appen.com/search/?createNewAlert=false&q=&optionsFacetsDD_country=BR",  # Brazil
        "https://jobs.appen.com/search/?createNewAlert=false&q=&optionsFacetsDD_country=CO",  # Colombia
        "https://jobs.appen.com/search/?createNewAlert=false&q=&optionsFacetsDD_country=MX",  # Mexico
        "https://jobs.appen.com/search/?createNewAlert=false&q=&optionsFacetsDD_customfield1=Remote",  # All remote
    ]
    
    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch opportunities from Appen"""
        all_jobs = []
        
        for url in self.URLS:
            await self._rate_limit()
            
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                    async with session.get(url, headers=headers, timeout=30) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            
                            # Find job rows
                            job_rows = soup.find_all('tr', class_='data-row')
                            
                            for row in job_rows:
                                try:
                                    job = self._parse_row(row)
                                    if job:
                                        all_jobs.append(job)
                                except Exception as e:
                                    continue
                        else:
                            print(f"[Appen] Error {response.status} for {url}")
            except Exception as e:
                print(f"[Appen] Error fetching {url}: {e}")
                continue
        
        return all_jobs
    
    def _parse_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a job row from Appen"""
        try:
            # Get title and link
            title_cell = row.find('td', class_='colTitle')
            if not title_cell:
                return None
            
            link_elem = title_cell.find('a')
            if not link_elem:
                return None
            
            title = link_elem.text.strip()
            job_path = link_elem.get('href', '')
            job_id = job_path.split('/')[-1] if '/' in job_path else job_path
            url = f"https://jobs.appen.com{job_path}" if job_path.startswith('/') else job_path
            
            # Get location
            location_cell = row.find('td', class_='colLocation')
            location = location_cell.text.strip() if location_cell else "Remote"
            
            # Get date posted
            date_cell = row.find('td', class_='colDate')
            date_posted = date_cell.text.strip() if date_cell else None
            
            return {
                "id": f"appen_{job_id}",
                "title": title,
                "url": url,
                "location": location,
                "date_posted": date_posted,
                "company": "Appen"
            }
            
        except Exception as e:
            return None
    
    def parse(self, raw_data: Dict[str, Any]) -> Optional[Opportunity]:
        """Parse into Opportunity"""
        try:
            title = raw_data.get("title", "")
            
            # All Appen jobs are microtasks with quick registration
            opp = Opportunity(
                source=self.source,
                source_id=raw_data["id"],
                title=title,
                company="Appen",
                description="Microtask opportunity for AI training, data labeling, or search evaluation. Low barrier to entry, work remotely.",
                url=raw_data["url"],
                location_type="remote",
                location_restrictions=[raw_data.get("location", "Remote"), "Worldwide"],
                salary_text="Per-task payment (varies by project)",
                tags=["microtask", "ai-training", "data-labeling", "flexible"],
                type=OpportunityType.MICROTASK,
                application_type=ApplicationType.QUICK_START,
                difficulty=1,  # Very low barrier
                raw_data=raw_data
            )
            
            opp.score = calculate_score(opp)
            return opp
            
        except Exception as e:
            print(f"[Appen] Parse error: {e}")
            return None
