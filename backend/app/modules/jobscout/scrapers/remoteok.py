"""RemoteOK scraper - JSON API"""

from datetime import datetime
from typing import List, Dict, Any, Optional

import aiohttp

from ..models import Opportunity
from ..scoring import classify_opportunity, calculate_score
from .base import BaseScraper, register_scraper


@register_scraper
class RemoteOKScraper(BaseScraper):
    """Scraper for RemoteOK.com API"""
    
    name = "remoteok"
    source = "remoteok"
    source_type = "api"
    rate_limit_delay = 1.0
    
    API_URL = "https://remoteok.com/api"
    
    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch jobs from RemoteOK API"""
        await self._rate_limit()
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json"
                }
                async with session.get(self.API_URL, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        # RemoteOK returns array directly, first element is metadata
                        if isinstance(data, list) and len(data) > 0:
                            # Skip first element (metadata) if it doesn't have an id
                            if "id" not in data[0]:
                                return data[1:]
                            return data
                        return data
                    else:
                        print(f"[RemoteOK] Error {response.status}")
                        return []
        except Exception as e:
            print(f"[RemoteOK] Fetch error: {e}")
            return []
    
    def parse(self, raw_data: Dict[str, Any]) -> Optional[Opportunity]:
        """Parse RemoteOK job into Opportunity"""
        try:
            job_id = str(raw_data.get("id", ""))
            if not job_id or job_id == "0":
                return None
            
            # Handle slug if present
            slug = raw_data.get("slug", "")
            if slug:
                job_id = f"{job_id}_{slug}"
            
            title = raw_data.get("position", "") or raw_data.get("title", "")
            company = raw_data.get("company", "")
            description = raw_data.get("description", "")
            
            # Location info
            location = raw_data.get("location", "")
            if not location:
                location = "Worldwide"
            
            # Tags
            tags = raw_data.get("tags", []) or []
            if isinstance(tags, str):
                tags = [tags]
            
            # Salary
            salary = raw_data.get("salary", "") or raw_data.get("salary_min", "")
            
            # URL
            slug = raw_data.get("slug", "")
            url = f"https://remoteok.com/remote-jobs/{slug}" if slug else ""
            
            # Classify
            opp_type, app_type, difficulty = classify_opportunity(title, description, company, url)
            
            opp = Opportunity(
                source=self.source,
                source_id=job_id,
                title=title,
                company=company,
                description=description[:2000] if description else None,
                url=url,
                location_type="remote",
                location_restrictions=[location],
                salary_text=salary if salary else "Not specified",
                tags=tags,
                type=opp_type,
                application_type=app_type,
                difficulty=difficulty,
                posted_at=self._parse_timestamp(raw_data.get("date")),
                raw_data=raw_data
            )
            
            opp.score = calculate_score(opp)
            return opp
            
        except Exception as e:
            print(f"[RemoteOK] Parse error: {e}")
            return None
    
    def _parse_timestamp(self, timestamp: Any) -> Optional[datetime]:
        """Parse timestamp from RemoteOK"""
        if not timestamp:
            return None
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp)
            return None
        except:
            return None
