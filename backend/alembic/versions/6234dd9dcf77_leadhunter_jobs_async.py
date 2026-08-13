"""leadhunter jobs async — solo cambios aditivos (crear tabla + columnas)

Revision ID: 6234dd9dcf77
Revises: 99662dfb6315
Create Date: 2026-08-12 18:20:44.285995

NOTA: la versión autogenerada por Alembic incluía drops de tablas jobscout
(opportunities, scout_runs, opportunity_views) y alters de tipos de columna
NUMERIC→Uuid. Eso es destructivo y NO se aplica. Esta migración es manual y
solamente aditiva: crea lead_hunter_jobs y agrega job_id a leads/lead_hunt_runs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6234dd9dcf77'
down_revision: Union[str, Sequence[str], None] = '99662dfb6315'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema (aditivo)."""
    op.create_table(
        'lead_hunter_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('project_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('criteria', sa.JSON(), nullable=True),
        sa.Column('progress', sa.String(length=32), nullable=True),
        sa.Column('results_count', sa.Integer(), nullable=False),
        sa.Column('duplicates_count', sa.Integer(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_lead_hunter_jobs_status'), 'lead_hunter_jobs', ['status'], unique=False)

    # job_id en leads (string, indexado, nullable — sin FK para no romper nada)
    op.add_column('leads', sa.Column('job_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_leads_job_id'), 'leads', ['job_id'], unique=False)

    # job_id en lead_hunt_runs
    op.add_column('lead_hunt_runs', sa.Column('job_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_lead_hunt_runs_job_id'), 'lead_hunt_runs', ['job_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_lead_hunt_runs_job_id'), table_name='lead_hunt_runs')
    op.drop_column('lead_hunt_runs', 'job_id')
    op.drop_index(op.f('ix_leads_job_id'), table_name='leads')
    op.drop_column('leads', 'job_id')
    op.drop_index(op.f('ix_lead_hunter_jobs_status'), table_name='lead_hunter_jobs')
    op.drop_table('lead_hunter_jobs')
