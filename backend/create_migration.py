# Script to create initial database migration
import sys
sys.path.append('.')

from alembic import command
from alembic.config import Config

# Create Alembic configuration
alembic_cfg = Config("alembic.ini")

# Create migration
command.revision(alembic_cfg, autogenerate=True, message="Initial migration")

print("✅ Migration created successfully!")
