"""SQLAlchemy models for JobScout module"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship

from app.database import Base


class OpportunityType(str, PyEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    FREELANCE = "freelance"
    MICROTASK = "microtask"
    SURVEY = "survey"
    GIG = "gig"
    INTERNSHIP = "internship"


class OpportunityStatus(str, PyEnum):
    NEW = "new"
    SEEN = "seen"
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    EXPIRED = "expired"


class ApplicationType(str, PyEnum):
    CV_EMAIL = "cv_email"
    PLATFORM_FORM = "platform_form"
    REGISTRATION_REQUIRED = "registration_required"
    ASSESSMENT_FIRST = "assessment_first"
    QUICK_START = "quick_start"


class Opportunity(Base):
    """A job, gig, or earning opportunity from any source"""
    __tablename__ = "opportunities"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Source info
    source = Column(String, nullable=False, index=True)  # remotive, wework, appen, etc.
    source_id = Column(String, nullable=False)  # ID from original source
    source_url = Column(String, nullable=True)
    
    # Classification
    type = Column(Enum(OpportunityType), nullable=False, default=OpportunityType.FULL_TIME)
    application_type = Column(Enum(ApplicationType), nullable=False, default=ApplicationType.PLATFORM_FORM)
    difficulty = Column(Integer, default=3)  # 1-5, 1 = lowest barrier
    
    # Content
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    requirements = Column(SQLiteJSON, default=list)  # List of requirements
    tags = Column(SQLiteJSON, default=list)  # Skills, technologies, etc.
    
    # Location
    location_type = Column(String, default="remote")  # remote, hybrid, onsite
    location_restrictions = Column(SQLiteJSON, default=list)  # ["worldwide"], ["US", "UK"], ["LATAM"]
    
    # Compensation
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String, default="USD")
    salary_period = Column(String, default="yearly")  # yearly, monthly, hourly, project
    salary_text = Column(String, nullable=True)  # Original text description
    
    # URLs
    url = Column(String, nullable=False)
    apply_url = Column(String, nullable=True)
    
    # Scoring
    score = Column(Integer, default=0)  # 0-100 calculated score
    
    # Status tracking
    status = Column(Enum(OpportunityStatus), default=OpportunityStatus.NEW, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    posted_at = Column(DateTime, nullable=True)  # When originally posted
    expires_at = Column(DateTime, nullable=True)
    
    # Application tracking
    applied_at = Column(DateTime, nullable=True)
    application_notes = Column(Text, nullable=True)
    
    # Raw data for debugging
    raw_data = Column(SQLiteJSON, nullable=True)

    __table_args__ = (
        # Unique constraint: same source + source_id = duplicate
        # Note: SQLite doesn't support conditional unique indexes, handle in code
    )

    def __repr__(self):
        return f"<Opportunity({self.source}: {self.title} @ {self.company})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "source": self.source,
            "type": self.type.value,
            "application_type": self.application_type.value,
            "difficulty": self.difficulty,
            "title": self.title,
            "company": self.company,
            "description": self.description,
            "requirements": self.requirements,
            "tags": self.tags,
            "location_type": self.location_type,
            "location_restrictions": self.location_restrictions,
            "salary_text": self.salary_text,
            "url": self.url,
            "apply_url": self.apply_url,
            "score": self.score,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
        }


class OpportunityView(Base):
    """Track when opportunities are viewed"""
    __tablename__ = "opportunity_views"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    opportunity_id = Column(String, ForeignKey("opportunities.id"), nullable=False)
    viewed_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String, default="api")  # api, telegram, dashboard
    
    opportunity = relationship("Opportunity", backref="views")


class ScoutRun(Base):
    """Track scraper runs"""
    __tablename__ = "scout_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)  # Which scraper ran
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="running")  # running, success, error
    jobs_found = Column(Integer, default=0)
    jobs_new = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
