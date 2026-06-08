"""Pydantic schemas for JobScout API"""

from datetime import datetime
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class OpportunityType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    FREELANCE = "freelance"
    MICROTASK = "microtask"
    SURVEY = "survey"
    GIG = "gig"
    INTERNSHIP = "internship"


class OpportunityStatus(str, Enum):
    NEW = "new"
    SEEN = "seen"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    EXPIRED = "expired"


class ApplicationType(str, Enum):
    CV_EMAIL = "cv_email"
    PLATFORM_FORM = "platform_form"
    REGISTRATION_REQUIRED = "registration_required"
    ASSESSMENT_FIRST = "assessment_first"
    QUICK_START = "quick_start"


class OpportunityBase(BaseModel):
    title: str
    company: str
    type: OpportunityType
    application_type: ApplicationType
    difficulty: int = Field(ge=1, le=5)
    location_restrictions: List[str]
    tags: List[str] = []
    score: int = Field(ge=0, le=100)


class OpportunityCreate(OpportunityBase):
    source: str
    source_id: str
    description: Optional[str] = None
    url: str
    apply_url: Optional[str] = None
    salary_text: Optional[str] = None
    requirements: List[str] = []


class OpportunityResponse(OpportunityBase):
    id: str
    source: str
    description: Optional[str]
    url: str
    apply_url: Optional[str]
    salary_text: Optional[str]
    requirements: List[str]
    status: OpportunityStatus
    created_at: datetime
    posted_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class OpportunityListResponse(BaseModel):
    items: List[OpportunityResponse]
    total: int
    page: int
    page_size: int


class OpportunityFilters(BaseModel):
    type: Optional[OpportunityType] = None
    types: Optional[List[OpportunityType]] = None
    status: Optional[OpportunityStatus] = None
    source: Optional[str] = None
    min_score: Optional[int] = Field(default=None, ge=0, le=100)
    max_difficulty: Optional[int] = Field(default=None, ge=1, le=5)
    location_friendly: Optional[bool] = None  # True = worldwide/LATAM only
    search: Optional[str] = None
    tags: Optional[List[str]] = None


class OpportunityUpdate(BaseModel):
    status: Optional[OpportunityStatus] = None
    application_notes: Optional[str] = None


class ScoutResult(BaseModel):
    source: str
    jobs_found: int
    jobs_new: int
    errors: List[str] = []


class ScoutAllResponse(BaseModel):
    results: List[ScoutResult]
    total_found: int
    total_new: int


class SourceInfo(BaseModel):
    name: str
    source: str
    source_type: str
    enabled: bool = True


class StatsResponse(BaseModel):
    total_opportunities: int
    by_source: dict[str, int]
    by_type: dict[str, int]
    by_status: dict[str, int]
    avg_score: float
    new_this_week: int
    applied_count: int
