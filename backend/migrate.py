# Script to run database migration
import sys
sys.path.append('.')

from alembic import command
from alembic.config import Config

# Create Alembic configuration
alembic_cfg = Config("alembic.ini")

# Run migration
command.upgrade(alembic_cfg, "head")

print("✅ Database migrated successfully!")
