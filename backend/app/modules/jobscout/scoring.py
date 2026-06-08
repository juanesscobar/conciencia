"""Scoring and classification for opportunities"""

from typing import List, Optional
from .models import Opportunity, OpportunityType, ApplicationType


# Keywords for scoring
HIGH_VALUE_KEYWORDS = [
    "senior", "lead", "principal", "architect", "staff",
    "python", "rust", "golang", "kubernetes", "aws", 
    "blockchain", "ai", "machine learning", "tensorflow", "pytorch",
    "distributed", "remote", "worldwide"
]

MEDIUM_VALUE_KEYWORDS = [
    "full stack", "backend", "frontend", "react", "node",
    "typescript", "docker", "sql", "nosql", "microservices",
    "fastapi", "django", "flask", "postgresql"
]

ENTRY_LEVEL_KEYWORDS = [
    "junior", "entry level", "entry-level", "beginner", 
    "no experience", "trainee", "intern", "internship",
    "student", "fresh graduate"
]

PARAGUAY_FRIENDLY_LOCATIONS = [
    "worldwide", "anywhere", "global", "remote", 
    "latam", "latin america", "south america", 
    "americas", "paraguay"
]

MICROTASK_PLATFORMS = [
    "appen", "toloka", "clickworker", "mturk", "amazon mechanical turk",
    "prolific", "usertesting", "trymata", "intellizoom", "userlytics"
]

FREELANCE_PLATFORMS = [
    "upwork", "fiverr", "toptal", "gun.io", "contra", 
    "peopleperhour", "freelancer"
]


def calculate_score(opportunity: Opportunity) -> int:
    """Calculate relevance score (0-100) for Paraguay-based developer
    
    Factors:
    - Location friendliness (worldwide/LATAM = high)
    - Low barrier to entry
    - Direct CV application preferred
    - Keywords match
    - Opportunity type preference
    """
    score = 0
    text = f"{opportunity.title} {opportunity.description or ''}".lower()
    
    # ===== LOCATION (max 25 pts) =====
    location_score = 0
    for loc in opportunity.location_restrictions or []:
        loc_lower = loc.lower()
        if any(friendly in loc_lower for friendly in PARAGUAY_FRIENDLY_LOCATIONS):
            if "worldwide" in loc_lower or "anywhere" in loc_lower or "global" in loc_lower:
                location_score = 25
                break
            elif "latam" in loc_lower or "latin america" in loc_lower:
                location_score = max(location_score, 22)
            elif "south america" in loc_lower or "americas" in loc_lower:
                location_score = max(location_score, 20)
            elif "paraguay" in loc_lower:
                location_score = max(location_score, 23)
    score += location_score
    
    # ===== BARRIER TO ENTRY (max 20 pts) =====
    difficulty_score = 0
    if opportunity.difficulty <= 1:
        difficulty_score = 20  # Very easy
    elif opportunity.difficulty == 2:
        difficulty_score = 15
    elif opportunity.difficulty == 3:
        difficulty_score = 10
    elif opportunity.difficulty == 4:
        difficulty_score = 5
    # difficulty 5 = 0 pts
    score += difficulty_score
    
    # ===== APPLICATION TYPE (max 15 pts) =====
    app_type_score = 0
    if opportunity.application_type == ApplicationType.CV_EMAIL:
        app_type_score = 15  # Best: direct application
    elif opportunity.application_type == ApplicationType.QUICK_START:
        app_type_score = 14  # Microtask-style immediate start
    elif opportunity.application_type == ApplicationType.PLATFORM_FORM:
        app_type_score = 10
    elif opportunity.application_type == ApplicationType.REGISTRATION_REQUIRED:
        app_type_score = 5
    elif opportunity.application_type == ApplicationType.ASSESSMENT_FIRST:
        app_type_score = 3  # Lowest: barrier before applying
    score += app_type_score
    
    # ===== OPPORTUNITY TYPE (max 15 pts) =====
    type_score = 0
    if opportunity.type == OpportunityType.MICROTASK:
        type_score = 15  # Quick money for PY
    elif opportunity.type == OpportunityType.FULL_TIME:
        type_score = 12  # Stable income
    elif opportunity.type == OpportunityType.FREELANCE:
        type_score = 10
    elif opportunity.type == OpportunityType.GIG:
        type_score = 10
    elif opportunity.type == OpportunityType.SURVEY:
        type_score = 8
    elif opportunity.type == OpportunityType.PART_TIME:
        type_score = 8
    score += type_score
    
    # ===== KEYWORDS (max 20 pts) =====
    keyword_score = 0
    for kw in HIGH_VALUE_KEYWORDS:
        if kw in text:
            keyword_score += 5
    for kw in MEDIUM_VALUE_KEYWORDS:
        if kw in text:
            keyword_score += 3
    for kw in ENTRY_LEVEL_KEYWORDS:
        if kw in text:
            keyword_score += 4  # Good for entry-level seekers
    
    score += min(keyword_score, 20)  # Cap at 20
    
    # ===== BONUS: Salary mentioned (max 5 pts) =====
    if opportunity.salary_text and opportunity.salary_text != "Not specified":
        score += 5
    
    return min(score, 100)


def classify_opportunity(title: str, description: Optional[str], company: str, url: str) -> tuple[OpportunityType, ApplicationType, int]:
    """Classify opportunity type and application method from content
    
    Returns: (opportunity_type, application_type, difficulty)
    """
    text = f"{title} {description or ''} {company}".lower()
    
    # Detect opportunity type
    opp_type = OpportunityType.FULL_TIME
    
    # Check for microtask platforms
    if any(platform in text for platform in MICROTASK_PLATFORMS):
        opp_type = OpportunityType.MICROTASK
    # Check for freelance platforms
    elif any(platform in text for platform in FREELANCE_PLATFORMS):
        opp_type = OpportunityType.FREELANCE
    # Check for survey/UX testing
    elif any(kw in text for kw in ["survey", "study", "user test", " usability test"]):
        opp_type = OpportunityType.SURVEY
    # Check for gig work
    elif any(kw in text for kw in ["gig", "task", "micro job", "small task"]):
        opp_type = OpportunityType.GIG
    # Check for internship
    elif any(kw in text for kw in ["intern", "internship", "trainee"]):
        opp_type = OpportunityType.INTERNSHIP
    # Check for part-time
    elif any(kw in text for kw in ["part-time", "part time", "20 hours", "20h/week"]):
        opp_type = OpportunityType.PART_TIME
    
    # Detect application type
    app_type = ApplicationType.PLATFORM_FORM
    difficulty = 3
    
    # Microtasks often have quick start
    if opp_type == OpportunityType.MICROTASK:
        app_type = ApplicationType.QUICK_START
        difficulty = 1
    
    # Surveys typically quick
    elif opp_type == OpportunityType.SURVEY:
        app_type = ApplicationType.QUICK_START
        difficulty = 1
    
    # Check for CV/email application mentions
    elif any(kw in text for kw in ["send cv", "send resume", "email your cv", "apply via email"]):
        app_type = ApplicationType.CV_EMAIL
        difficulty = 2
    
    # Check for registration requirements
    elif any(kw in text for kw in ["create account", "sign up", "register", "platform required"]):
        app_type = ApplicationType.REGISTRATION_REQUIRED
        difficulty = 2 if opp_type == OpportunityType.MICROTASK else 3
    
    # Check for assessment/tests
    elif any(kw in text for kw in ["assessment", "test required", "qualification", "certification needed"]):
        app_type = ApplicationType.ASSESSMENT_FIRST
        difficulty = 4
    
    return opp_type, app_type, difficulty


def is_paraguay_friendly(location_restrictions: List[str]) -> bool:
    """Check if opportunity is available for Paraguay-based applicants"""
    if not location_restrictions:
        return True  # Assume worldwide if not specified
    
    for loc in location_restrictions:
        loc_lower = loc.lower()
        if any(friendly in loc_lower for friendly in PARAGUAY_FRIENDLY_LOCATIONS):
            return True
    
    return False
