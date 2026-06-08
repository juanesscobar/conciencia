"""Remotive API scraper - Remote tech jobs"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import asyncio

import aiohttp

from ..models import Opportunity, OpportunityType, OpportunityStatus
from ..scoring import classify_opportunity, calculate_score
from .base import BaseScraper, register_scraper


@register_scraper
class RemotiveScraper(BaseScraper):
    """Scraper for Remotive.com API"""
    
    name = "remotive"
    source = "remotive"
    source_type = "api"
    rate_limit_delay = 1.0
    
    API_URL = "https://remotive.com/api/remote-jobs"
    
    # Categories we care about
    CATEGORIES = [
        "software-development",
        "devops-sysadmin",
        "qa-testing",
        "data-science",
        "machine-learning",
        "web-development",
        "mobile-development"
    ]
    
    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch jobs from Remotive API"""
        all_jobs = []
        
        # Fetch each category
        for category in self.CATEGORIES:
            await self._rate_limit()
            
            try:
                async with aiohttp.ClientSession() as session:
                    params = {"category": category}
                    async with session.get(self.API_URL, params=params, timeout=30) as response:
                        if response.status == 200:
                            data = await response.json()
                            jobs = data.get("jobs", [])
                            all_jobs.extend(jobs)
                        else:
                            print(f"[Remotive] Error {response.status} for category {category}")
            except Exception as e:
                print(f"[Remotive] Error fetching {category}: {e}")
                continue
        
        # Also fetch general jobs (no category filter)
        await self._rate_limit()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.API_URL, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        jobs = data.get("jobs", [])
                        all_jobs.extend(jobs)
        except Exception as e:
            print(f"[Remotive] Error fetching general jobs: {e}")
        
        # Deduplicate by id
        seen_ids = set()
        unique_jobs = []
        for job in all_jobs:
            job_id = str(job.get("id", ""))
            if job_id and job_id not in seen_ids:
                seen_ids.add(job_id)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def parse(self, raw_data: Dict[str, Any]) -> Optional[Opportunity]:
        """Parse Remotive job into Opportunity"""
        try:
            job_id = str(raw_data.get("id", ""))
            if not job_id:
                return None
            
            title = raw_data.get("title", "")
            company = raw_data.get("company_name", "")
            description = raw_data.get("description", "")
            
            # Get location
            location = raw_data.get("candidate_required_location", "Worldwide")
            location_restrictions = [location]
            
            # Parse salary if available
            salary = raw_data.get("salary", "")
            
            # Extract tags from category
            tags = []
            category = raw_data.get("category", "")
            if category:
                tags.append(category)
            
            # Classify
            opp_type, app_type, difficulty = classify_opportunity(title, description, company, "")
            
            # Create opportunity
            opp = Opportunity(
                source=self.source,
                source_id=job_id,
                title=title,
                company=company,
                description=description[:2000] if description else None,  # Limit length
                url=raw_data.get("url", ""),
                location_type="remote",
                location_restrictions=location_restrictions,
                salary_text=salary if salary else "Not specified",
                tags=tags,
                type=opp_type,
                application_type=app_type,
                difficulty=difficulty,
                job_type=raw_data.get("job_type", "full_time"),
                posted_at=self._parse_date(raw_data.get("publication_date")),
                raw_data=raw_data
            )
            
            # Calculate score
            opp.score = calculate_score(opp)
            
            return opp
            
        except Exception as e:
            print(f"[Remotive] Parse error: {e}")
            return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO date string"""
        if not date_str:
            return None
        try:
            # Handle various ISO formats
            date_str = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(date_str)
        except:
            return None
