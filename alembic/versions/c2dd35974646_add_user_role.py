"""add user role

Revision ID: c2dd35974646
Revises: d0c27179b4ee
Create Date: 2025-11-17 18:16:08.054430

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2dd35974646'
down_revision: Union[str, Sequence[str], None] = 'd0c27179b4ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("users", sa.Column("role", sa.String(length=50), nullable=False, server_default="operator"))
    op.alter_column("users", "role", server_default=None)

def downgrade():
    op.drop_column("users", "role")
