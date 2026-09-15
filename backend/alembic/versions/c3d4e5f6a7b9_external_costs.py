"""mission_runs.external_costs — Fase L (Economics)

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b9'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mission_runs', sa.Column('external_costs', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('mission_runs', 'external_costs')
