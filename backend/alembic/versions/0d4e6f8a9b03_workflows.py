"""workflows + workflow_runs — aditivo

Revision ID: 0d4e6f8a9b03
Revises: 9c3d5e7f8a02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0d4e6f8a9b03'
down_revision: Union[str, Sequence[str], None] = '9c3d5e7f8a02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'workflows',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('project_id', sa.String(length=50), nullable=True),
        sa.Column('definition', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('current_step', sa.Integer(), nullable=True),
        sa.Column('error', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'workflow_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workflow_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('step_results', sa.JSON(), nullable=True),
        sa.Column('current_step', sa.Integer(), nullable=True),
        sa.Column('paused_at', sa.DateTime(), nullable=True),
        sa.Column('error', sa.String(length=500), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_workflow_runs_workflow_id', 'workflow_runs', ['workflow_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_workflow_runs_workflow_id', table_name='workflow_runs')
    op.drop_table('workflow_runs')
    op.drop_table('workflows')
