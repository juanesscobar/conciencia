"""JobScout service layer - business logic"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .models import Opportunity, OpportunityStatus, ScoutRun
from .scrapers import get_all_scrapers, run_all_scrapers
from .schemas import OpportunityFilters, OpportunityUpdate


class JobScoutService:
    """Service for managing opportunities and scouting"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ===== Opportunity CRUD =====
    
    def get_opportunities(
        self,
        filters: Optional[OpportunityFilters] = None,
        skip: int = 0,
        limit: int = 50,
        order_by: str = "score"
    ) -> tuple[List[Opportunity], int]:
        """Get opportunities with filters"""
        query = self.db.query(Opportunity)
        
        if filters:
            if filters.type:
                query = query.filter(Opportunity.type == filters.type)
            if filters.types:
                query = query.filter(Opportunity.type.in_(filters.types))
            if filters.status:
                query = query.filter(Opportunity.status == filters.status)
            if filters.source:
                query = query.filter(Opportunity.source == filters.source)
            if filters.min_score is not None:
                query = query.filter(Opportunity.score >= filters.min_score)
            if filters.max_difficulty is not None:
                query = query.filter(Opportunity.difficulty <= filters.max_difficulty)
            if filters.location_friendly:
                # Filter for Paraguay-friendly locations
                query = query.filter(
                    Opportunity.location_restrictions.contains(["worldwide"]) |
                    Opportunity.location_restrictions.contains(["Worldwide"]) |
                    Opportunity.location_restrictions.contains(["latam"]) |
                    Opportunity.location_restrictions.contains(["LATAM"])
                )
            if filters.search:
                search = f"%{filters.search}%"
                query = query.filter(
                    Opportunity.title.ilike(search) |
                    Opportunity.company.ilike(search) |
                    Opportunity.description.ilike(search)
                )
            if filters.tags:
                for tag in filters.tags:
                    query = query.filter(Opportunity.tags.contains([tag]))
        
        # Get total count
        total = query.count()
        
        # Apply ordering
        if order_by == "score":
            query = query.order_by(desc(Opportunity.score))
        elif order_by == "newest":
            query = query.order_by(desc(Opportunity.created_at))
        elif order_by == "posted":
            query = query.order_by(desc(Opportunity.posted_at))
        
        # Apply pagination
        opportunities = query.offset(skip).limit(limit).all()
        
        return opportunities, total
    
    def get_opportunity(self, opportunity_id: str) -> Optional[Opportunity]:
        """Get single opportunity by ID"""
        return self.db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    
    def get_opportunity_by_source(self, source: str, source_id: str) -> Optional[Opportunity]:
        """Get opportunity by source and source_id (for deduplication)"""
        return self.db.query(Opportunity).filter(
            Opportunity.source == source,
            Opportunity.source_id == source_id
        ).first()
    
    def create_or_update_opportunity(self, opp: Opportunity) -> tuple[Opportunity, bool]:
        """Create or update opportunity. Returns (opportunity, is_new)"""
        existing = self.get_opportunity_by_source(opp.source, opp.source_id)
        
        if existing:
            # Update existing
            existing.title = opp.title
            existing.company = opp.company
            existing.description = opp.description
            existing.url = opp.url
            existing.score = opp.score
            existing.tags = opp.tags
            existing.salary_text = opp.salary_text
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing, False
        else:
            # Create new
            self.db.add(opp)
            self.db.commit()
            self.db.refresh(opp)
            return opp, True
    
    def update_opportunity(
        self,
        opportunity_id: str,
        update: OpportunityUpdate
    ) -> Optional[Opportunity]:
        """Update opportunity"""
        opp = self.get_opportunity(opportunity_id)
        if not opp:
            return None
        
        if update.status:
            opp.status = update.status
            if update.status == OpportunityStatus.APPLIED:
                opp.applied_at = datetime.utcnow()
        
        if update.application_notes:
            opp.application_notes = update.application_notes
        
        opp.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(opp)
        return opp
    
    def mark_as_seen(self, opportunity_id: str) -> bool:
        """Mark opportunity as seen"""
        opp = self.get_opportunity(opportunity_id)
        if not opp:
            return False
        
        if opp.status == OpportunityStatus.NEW:
            opp.status = OpportunityStatus.SEEN
            self.db.commit()
        return True
    
    # ===== Scouting =====
    
    async def run_scout(self, source: Optional[str] = None) -> Dict[str, Any]:
        """Run scout for a specific source or all sources"""
        results = []
        total_found = 0
        total_new = 0
        
        if source:
            # Run specific scraper
            scraper = get_all_scrapers().get(source)
            if not scraper:
                return {"error": f"Scraper '{source}' not found"}
            
            try:
                found, parsed, opps = await scraper.scout()
                new_count = 0
                for opp in opps:
                    _, is_new = self.create_or_update_opportunity(opp)
                    if is_new:
                        new_count += 1
                
                results.append({
                    "source": source,
                    "jobs_found": found,
                    "jobs_new": new_count,
                    "errors": []
                })
                total_found += found
                total_new += new_count
            except Exception as e:
                results.append({
                    "source": source,
                    "jobs_found": 0,
                    "jobs_new": 0,
                    "errors": [str(e)]
                })
        else:
            # Run all scrapers
            all_results = await run_all_scrapers()
            
            for name, (found, parsed, opps) in all_results.items():
                new_count = 0
                for opp in opps:
                    _, is_new = self.create_or_update_opportunity(opp)
                    if is_new:
                        new_count += 1
                
                results.append({
                    "source": name,
                    "jobs_found": found,
                    "jobs_new": new_count,
                    "errors": []
                })
                total_found += found
                total_new += new_count
        
        return {
            "results": results,
            "total_found": total_found,
            "total_new": total_new
        }
    
    # ===== Stats =====
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about opportunities"""
        # Total count
        total = self.db.query(Opportunity).count()
        
        # By source
        by_source = {}
        source_counts = self.db.query(
            Opportunity.source,
            func.count(Opportunity.id)
        ).group_by(Opportunity.source).all()
        for source, count in source_counts:
            by_source[source] = count
        
        # By type
        by_type = {}
        type_counts = self.db.query(
            Opportunity.type,
            func.count(Opportunity.id)
        ).group_by(Opportunity.type).all()
        for type_, count in type_counts:
            by_type[type_.value if hasattr(type_, 'value') else str(type_)] = count
        
        # By status
        by_status = {}
        status_counts = self.db.query(
            Opportunity.status,
            func.count(Opportunity.id)
        ).group_by(Opportunity.status).all()
        for status, count in status_counts:
            by_status[status.value if hasattr(status, 'value') else str(status)] = count
        
        # Average score
        avg_score = self.db.query(func.avg(Opportunity.score)).scalar() or 0
        
        # New this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_this_week = self.db.query(Opportunity).filter(
            Opportunity.created_at >= week_ago
        ).count()
        
        # Applied count
        applied_count = self.db.query(Opportunity).filter(
            Opportunity.status == OpportunityStatus.APPLIED
        ).count()
        
        return {
            "total_opportunities": total,
            "by_source": by_source,
            "by_type": by_type,
            "by_status": by_status,
            "avg_score": round(float(avg_score), 1),
            "new_this_week": new_this_week,
            "applied_count": applied_count
        }
    
    def get_digest_opportunities(self, limit: int = 10) -> List[Opportunity]:
        """Get top opportunities for digest (new + high score)"""
        return self.db.query(Opportunity).filter(
            Opportunity.status == OpportunityStatus.NEW
        ).order_by(desc(Opportunity.score)).limit(limit).all()
