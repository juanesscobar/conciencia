"""task_dependencies + estados READY/ASSIGNED/BLOCKED — aditivo

Revision ID: 8b2c4d5e6f01
Revises: 7a1e4f2c9d01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8b2c4d5e6f01'
down_revision: Union[str, Sequence[str], None] = '7a1e4f2c9d01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'task_dependencies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('depends_on_id', sa.String(), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', 'depends_on_id', name='uq_task_dep'),
    )
    op.create_index(op.f('ix_task_dependencies_task_id'), 'task_dependencies', ['task_id'], unique=False)
    op.create_index(op.f('ix_task_dependencies_depends_on_id'), 'task_dependencies', ['depends_on_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_task_dependencies_depends_on_id'), table_name='task_dependencies')
    op.drop_index(op.f('ix_task_dependencies_task_id'), table_name='task_dependencies')
    op.drop_table('task_dependencies')
