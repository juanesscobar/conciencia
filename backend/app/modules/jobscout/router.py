"""JobScout API router"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db

from .models import OpportunityStatus
from .schemas import (
    OpportunityResponse,
    OpportunityListResponse,
    OpportunityFilters,
    OpportunityUpdate,
    ScoutAllResponse,
    ScoutResult,
    SourceInfo,
    StatsResponse
)
from .service import JobScoutService
from .scrapers import get_all_scrapers

router = APIRouter(prefix="/api/v1/jobscout", tags=["jobscout"])


def get_service(db: Session = Depends(get_db)):
    return JobScoutService(db)


@router.get("/opportunities", response_model=OpportunityListResponse)
async def list_opportunities(
    type: Optional[str] = None,
    types: Optional[List[str]] = Query(None),
    status: Optional[str] = None,
    source: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_difficulty: Optional[int] = Query(None, ge=1, le=5),
    location_friendly: Optional[bool] = None,
    search: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    order_by: str = Query("score", regex="^(score|newest|posted)$"),
    service: JobScoutService = Depends(get_service)
):
    """List opportunities with filters"""
    filters = OpportunityFilters(
        type=type,
        types=types,
        status=status,
        source=source,
        min_score=min_score,
        max_difficulty=max_difficulty,
        location_friendly=location_friendly,
        search=search,
        tags=tags
    )
    
    skip = (page - 1) * page_size
    opportunities, total = service.get_opportunities(
        filters=filters,
        skip=skip,
        limit=page_size,
        order_by=order_by
    )
    
    return OpportunityListResponse(
        items=[opp.to_dict() for opp in opportunities],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: str,
    service: JobScoutService = Depends(get_service)
):
    """Get single opportunity"""
    opp = service.get_opportunity(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp.to_dict()


@router.post("/opportunities/{opportunity_id}/seen")
async def mark_as_seen(
    opportunity_id: str,
    service: JobScoutService = Depends(get_service)
):
    """Mark opportunity as seen"""
    success = service.mark_as_seen(opportunity_id)
    if not success:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"status": "marked_as_seen"}


@router.post("/opportunities/{opportunity_id}/apply")
async def apply_to_opportunity(
    opportunity_id: str,
    notes: Optional[str] = None,
    service: JobScoutService = Depends(get_service)
):
    """Mark opportunity as applied"""
    update = OpportunityUpdate(
        status=OpportunityStatus.APPLIED,
        application_notes=notes
    )
    opp = service.update_opportunity(opportunity_id, update)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"status": "marked_as_applied", "opportunity_id": opportunity_id}


@router.post("/opportunities/{opportunity_id}/skip")
async def skip_opportunity(
    opportunity_id: str,
    service: JobScoutService = Depends(get_service)
):
    """Skip/mark opportunity as seen without applying"""
    update = OpportunityUpdate(status=OpportunityStatus.SEEN)
    opp = service.update_opportunity(opportunity_id, update)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"status": "skipped"}


@router.post("/scout", response_model=ScoutAllResponse)
async def run_scout(
    source: Optional[str] = None,
    service: JobScoutService = Depends(get_service)
):
    """Run scout to fetch new opportunities"""
    result = await service.run_scout(source)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return ScoutAllResponse(
        results=[ScoutResult(**r) for r in result["results"]],
        total_found=result["total_found"],
        total_new=result["total_new"]
    )


@router.get("/sources", response_model=List[SourceInfo])
async def list_sources():
    """List available scraper sources"""
    scrapers = get_all_scrapers()
    return [
        SourceInfo(
            name=s.name,
            source=s.source,
            source_type=s.source_type
        )
        for s in scrapers.values()
    ]


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    service: JobScoutService = Depends(get_service)
):
    """Get JobScout statistics"""
    stats = service.get_stats()
    return StatsResponse(**stats)


@router.get("/digest")
async def get_digest(
    limit: int = Query(10, ge=1, le=50),
    service: JobScoutService = Depends(get_service)
):
    """Get opportunities for digest (new + high score)"""
    opps = service.get_digest_opportunities(limit)
    return {
        "opportunities": [opp.to_dict() for opp in opps],
        "count": len(opps)
    }
