"""leadhunter: columnas de normalización para dedupe v2 (spec §12)

Revision ID: a1b2c3d4e5f6
Revises: 0d4e6f8a9b03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '0d4e6f8a9b03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega normalized_name / normalized_domain / normalized_phone a leads (dedupe v2 indexado)."""
    inspector = sa.inspect(op.get_bind())
    columns = {column['name'] for column in inspector.get_columns('leads')}
    for name in ('normalized_name', 'normalized_domain', 'normalized_phone'):
        if name not in columns:
            op.add_column('leads', sa.Column(name, sa.String(), nullable=True))
    indexes = {index['name'] for index in inspector.get_indexes('leads')}
    for name, column in (
        ('ix_leads_normalized_name', 'normalized_name'),
        ('ix_leads_normalized_domain', 'normalized_domain'),
        ('ix_leads_normalized_phone', 'normalized_phone'),
    ):
        if name not in indexes:
            op.create_index(name, 'leads', [column])


def downgrade() -> None:
    op.drop_index('ix_leads_normalized_phone', table_name='leads')
    op.drop_index('ix_leads_normalized_domain', table_name='leads')
    op.drop_index('ix_leads_normalized_name', table_name='leads')
    op.drop_column('leads', 'normalized_phone')
    op.drop_column('leads', 'normalized_domain')
    op.drop_column('leads', 'normalized_name')
