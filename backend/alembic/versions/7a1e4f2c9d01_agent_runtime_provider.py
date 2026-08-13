"""agent runtime/provider/model + health registry — aditivo

Revision ID: 7a1e4f2c9d01
Revises: 6234dd9dcf77
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7a1e4f2c9d01'
down_revision: Union[str, Sequence[str], None] = '6234dd9dcf77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega ejes runtime/provider/model y health registry al agente (aditivo)."""
    op.add_column('agents', sa.Column('runtime', sa.String(length=20), nullable=False, server_default='generic'))
    op.add_column('agents', sa.Column('provider', sa.String(length=20), nullable=False, server_default='deepseek'))
    op.add_column('agents', sa.Column('model', sa.String(length=100), nullable=True))
    op.add_column('agents', sa.Column('workspace', sa.String(length=255), nullable=True))
    op.add_column('agents', sa.Column('health_status', sa.String(length=20), nullable=True, server_default='unknown'))
    op.add_column('agents', sa.Column('last_heartbeat', sa.DateTime(), nullable=True))
    op.add_column('agents', sa.Column('version', sa.String(length=50), nullable=True))
    op.add_column('agents', sa.Column('availability', sa.String(length=20), nullable=True, server_default='available'))


def downgrade() -> None:
    op.drop_column('agents', 'availability')
    op.drop_column('agents', 'version')
    op.drop_column('agents', 'last_heartbeat')
    op.drop_column('agents', 'health_status')
    op.drop_column('agents', 'workspace')
    op.drop_column('agents', 'model')
    op.drop_column('agents', 'provider')
    op.drop_column('agents', 'runtime')
