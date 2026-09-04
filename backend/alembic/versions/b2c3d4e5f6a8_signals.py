"""signals + evidence — Fase I (Signals + Evidence)

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'signals',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('mission_id', sa.Uuid(), nullable=False),
        sa.Column('type', sa.String(length=30), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('workflow_run_id', sa.String(length=50), nullable=True),
        sa.Column('mission_run_id', sa.Uuid(), nullable=True),
        sa.Column('source_step', sa.String(length=100), nullable=True),
        sa.Column('agent_id', sa.Uuid(), nullable=True),
        sa.Column('agent_name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['mission_id'], ['missions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_signals_mission_id', 'signals', ['mission_id'], unique=False)
    op.create_table(
        'evidence',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('signal_id', sa.Uuid(), nullable=False),
        sa.Column('kind', sa.String(length=30), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_evidence_signal_id', 'evidence', ['signal_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_evidence_signal_id', table_name='evidence')
    op.drop_table('evidence')
    op.drop_index('ix_signals_mission_id', table_name='signals')
    op.drop_table('signals')
