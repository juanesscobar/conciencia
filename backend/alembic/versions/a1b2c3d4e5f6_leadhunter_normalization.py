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
    op.add_column('leads', sa.Column('normalized_name', sa.String(), nullable=True))
    op.add_column('leads', sa.Column('normalized_domain', sa.String(), nullable=True))
    op.add_column('leads', sa.Column('normalized_phone', sa.String(), nullable=True))
    op.create_index('ix_leads_normalized_name', 'leads', ['normalized_name'])
    op.create_index('ix_leads_normalized_domain', 'leads', ['normalized_domain'])
    op.create_index('ix_leads_normalized_phone', 'leads', ['normalized_phone'])


def downgrade() -> None:
    op.drop_index('ix_leads_normalized_phone', table_name='leads')
    op.drop_index('ix_leads_normalized_domain', table_name='leads')
    op.drop_index('ix_leads_normalized_name', table_name='leads')
    op.drop_column('leads', 'normalized_phone')
    op.drop_column('leads', 'normalized_domain')
    op.drop_column('leads', 'normalized_name')
