"""add user role

Revision ID: 47c55b82355d
Revises: c2dd35974646
Create Date: 2025-11-17 18:19:26.363161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47c55b82355d'
down_revision: Union[str, Sequence[str], None] = 'c2dd35974646'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("users", sa.Column("role", sa.String(length=50), nullable=False, server_default="operator"))
    op.alter_column("users", "role", server_default=None)

def downgrade():
    op.drop_column("users", "role")