"""audit_events append-only — aditivo

Revision ID: 9c3d5e7f8a02
Revises: 8b2c4d5e6f01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9c3d5e7f8a02'
down_revision: Union[str, Sequence[str], None] = '8b2c4d5e6f01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('actor', sa.String(length=100), nullable=True),
        sa.Column('actor_type', sa.String(length=20), nullable=True),
        sa.Column('project_id', sa.String(length=50), nullable=True),
        sa.Column('task_id', sa.String(length=50), nullable=True),
        sa.Column('event_type', sa.String(length=80), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('correlation_id', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_ts', 'audit_events', ['timestamp'], unique=False)
    op.create_index('ix_audit_type', 'audit_events', ['event_type'], unique=False)
    op.create_index('ix_audit_actor', 'audit_events', ['actor'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_audit_actor', table_name='audit_events')
    op.drop_index('ix_audit_type', table_name='audit_events')
    op.drop_index('ix_audit_ts', table_name='audit_events')
    op.drop_table('audit_events')
