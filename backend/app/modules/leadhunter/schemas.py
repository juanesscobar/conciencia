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
    # --- Fase 4: ranking/scoring separados + data quality (aditivo) ---
    search_relevance: Optional[float] = None      # 0-100, dependiente de la query
    opportunity_score: Optional[int] = None       # 0-100, señales comerciales
    data_quality: Optional[int] = None            # 0-100, completitud+frescura+fuente
    reasons: Optional[List[str]] = None           # "Why this lead matches" (spec §34)


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
    meta: Optional[Dict[str, Any]] = None
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


class SendProposalRequest(BaseModel):
    channel: Optional[str] = None  # email | whatsapp | link
    to_email: Optional[str] = None


class SavedLeadListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None


class SavedLeadListResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    lead_count: int = 0
    created_at: Optional[str] = None


class SavedLeadListDetailResponse(SavedLeadListResponse):
    leads: List[LeadResponse] = []


class SavedLeadListAddRequest(BaseModel):
    lead_id: str


class LeadSavedSearchCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    filters: Optional[Dict[str, Any]] = None


class LeadSavedSearchResponse(BaseModel):
    id: str
    name: str
    filters: Dict[str, Any] = {}
    created_at: Optional[str] = None


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LeadHunterJobCreate(BaseModel):
    name: Optional[str] = None
    project_id: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None  # {source, limit, industry, region...}


class LeadHunterJobResponse(BaseModel):
    id: str
    name: Optional[str] = None
    project_id: Optional[str] = None
    status: str
    criteria: Optional[Dict[str, Any]] = None
    progress: Optional[str] = None
    results_count: int = 0
    duplicates_count: int = 0
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class LeadHunterJobListResponse(BaseModel):
    items: List[LeadHunterJobResponse]
    total: int


# --- Fase 4: RankingWeights (spec §15/§16) ---
class RankingWeights(BaseModel):
    relevance: Dict[str, float] = Field(default_factory=dict)
    lead: Dict[str, float] = Field(default_factory=dict)
    opportunity: Dict[str, float] = Field(default_factory=dict)


# --- Fase 5: búsqueda semántica (spec §14) ---
class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(20, ge=1, le=100)


class SemanticSearchResult(BaseModel):
    items: List[LeadResponse] = []
    total: int = 0
    query: str
    backend: str
    model: str
    simulated: bool = False


class SemanticStatus(BaseModel):
    enabled: bool
    backend: str
    model: str
    simulated: bool
    indexed: int
