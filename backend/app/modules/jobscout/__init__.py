"""JobScout module for Mission Control - Opportunity hunting system"""

from .models import Opportunity, OpportunityType, OpportunityStatus
from .scoring import calculate_score
from .classifier import classify_opportunity

__all__ = ["Opportunity", "OpportunityType", "OpportunityStatus", "calculate_score", "classify_opportunity"]
