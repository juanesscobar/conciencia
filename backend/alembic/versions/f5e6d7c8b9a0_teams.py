"""teams + missions.team_id — Fase F (Agent/Team Orchestration)

Revision ID: f5e6d7c8b9a0
Revises: a1b2c3d4e5f6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f5e6d7c8b9a0'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'teams',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('purpose', sa.String(length=255), nullable=True),
        sa.Column('emoji', sa.String(length=10), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('member_ids', sa.JSON(), nullable=True),
        sa.Column('default_runtime', sa.String(length=50), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('missions', sa.Column('team_id', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('missions', 'team_id')
    op.drop_table('teams')
