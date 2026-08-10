"""Pydantic schemas for Lead Hunter API."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, EmailStr


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    WON = "won"
    LOST = "lost"


class LeadCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    source: str = "manual"
    industry: Optional[str] = None
    segment: Optional[str] = None
    region: Optional[str] = None
    status: LeadStatus = LeadStatus.NEW
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LeadUpdate(BaseModel):
    company: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    source: Optional[str] = None
    industry: Optional[str] = None
    segment: Optional[str] = None
    region: Optional[str] = None
    status: Optional[LeadStatus] = None
    score: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LeadIntake(BaseModel):
    """Webhook público para captura de leads (landings, formularios)."""
    company: str = Field(..., min_length=1, max_length=200)
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    segment: Optional[str] = None
    region: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LeadResponse(BaseModel):
    id: str
    company: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    source: str
    industry: Optional[str] = None
    segment: Optional[str] = None
    region: Optional[str] = None
    status: str
    score: int
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    online_presence: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class LeadListResponse(BaseModel):
    items: List[LeadResponse]
    total: int
    page: int
    page_size: int


class LeadStats(BaseModel):
    total: int
    by_status: Dict[str, int]
    by_source: Dict[str, int]
    avg_score: float
    top_sources: List[Dict[str, Any]]


class HuntSourceInfo(BaseModel):
    name: str
    label: str
    description: str
    enabled: bool


class HuntRunResult(BaseModel):
    source: str
    found: int = 0
    added: int = 0
    duplicates: int = 0
    status: str = "completed"
    error: Optional[str] = None


class HuntSummary(BaseModel):
    results: List[HuntRunResult]
    total_found: int
    total_added: int
    total_duplicates: int


class HuntRunResponse(BaseModel):
    id: str
    source: str
    status: str
    found: int = 0
    added: int = 0
    duplicates: int = 0
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class EnrichResult(BaseModel):
    changed: bool
    email: Optional[str] = None
    phone: Optional[str] = None
    fetched: bool = False
    reason: Optional[str] = None


class LeadEventResponse(BaseModel):
    id: str
    lead_id: str
    event_type: str
    description: Optional[str] = None
    created_at: Optional[str] = None


class LeadProposalCreate(BaseModel):
    title: Optional[str] = None
    content: str


class LeadProposalResponse(BaseModel):
    id: str
    lead_id: str
    title: Optional[str] = None
    content: str
    status: str
    model: Optional[str] = None
    created_at: Optional[str] = None
    sent_at: Optional[str] = None


class ActionRequest(BaseModel):
    reason: Optional[str] = None
    note: Optional[str] = None


class ImportResult(BaseModel):
    total: int
    added: int
    duplicates: int
    errors: int = 0
