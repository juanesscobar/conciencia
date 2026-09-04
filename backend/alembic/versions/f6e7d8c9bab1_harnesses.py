"""harnesses + missions.harness_id — Fase G (Harness Layer)

Revision ID: f6e7d8c9bab1
Revises: f5e6d7c8b9a0
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f6e7d8c9bab1'
down_revision: Union[str, Sequence[str], None] = 'f5e6d7c8b9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'harnesses',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('spec', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('versions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.add_column('missions', sa.Column('harness_id', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('missions', 'harness_id')
    op.drop_table('harnesses')
