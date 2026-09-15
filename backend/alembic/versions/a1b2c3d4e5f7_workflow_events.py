"""workflow_runs.events — Fase H (Observability)

Revision ID: a1b2c3d4e5f7
Revises: f6e7d8c9bab1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'f6e7d8c9bab1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('workflow_runs', sa.Column('events', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('workflow_runs', 'events')
