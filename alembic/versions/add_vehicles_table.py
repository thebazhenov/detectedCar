"""add vehicles table

Revision ID: add_vehicles_table
Revises: 47c55b82355d
Create Date: 2025-01-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_vehicles_table'
down_revision: Union[str, Sequence[str], None] = '47c55b82355d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('vehicles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('license_plate', sa.String(length=20), nullable=False),
    sa.Column('owner_name', sa.String(length=255), nullable=False),
    sa.Column('notes', sa.String(length=1000), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_vehicles_license_plate'), 'vehicles', ['license_plate'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_vehicles_license_plate'), table_name='vehicles')
    op.drop_table('vehicles')

