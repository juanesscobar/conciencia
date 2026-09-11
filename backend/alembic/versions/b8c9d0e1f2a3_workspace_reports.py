"""Allow workspace-scoped report deliverables.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    nullable = next(column['nullable'] for column in sa.inspect(op.get_bind()).get_columns('deliverables') if column['name'] == 'project_id')
    if nullable:
        return
    with op.batch_alter_table("deliverables") as batch:
        batch.alter_column("project_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("deliverables") as batch:
        batch.alter_column("project_id", existing_type=None, nullable=False)
