"""add plate

Revision ID: c39df08ba1c4
Revises: add_vehicles_table
Create Date: 2025-11-30 21:33:00.276882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c39df08ba1c4'
down_revision: Union[str, Sequence[str], None] = 'add_vehicles_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
