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
    status: str
    score: int
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
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
