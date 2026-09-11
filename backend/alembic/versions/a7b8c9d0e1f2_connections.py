"""connections registry for governed external integration.

Revision ID: a7b8c9d0e1f2
Revises: f6e7d8c9bab1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6e7d8c9bab1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("config_reference", sa.Text(), nullable=True),
        sa.Column("last_check", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_connections_name", "connections", ["name"])


def downgrade() -> None:
    op.drop_index("ix_connections_name", table_name="connections")
    op.drop_table("connections")
