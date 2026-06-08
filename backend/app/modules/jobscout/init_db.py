"""Initialize JobScout database tables"""

from app.database import engine, Base
from app.modules.jobscout.models import Opportunity, OpportunityView, ScoutRun

def init_jobscout_tables():
    """Create JobScout tables"""
    print("Creating JobScout tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ JobScout tables created")

if __name__ == "__main__":
    init_jobscout_tables()
