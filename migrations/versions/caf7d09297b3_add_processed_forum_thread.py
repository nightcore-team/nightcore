"""empty message

Revision ID: caf7d09297b3
Revises: 9540501ccde5
Create Date: 2026-02-23 20:04:45.298054

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'caf7d09297b3'
down_revision: Union[str, Sequence[str], None] = '9540501ccde5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("processedforumthread", sa.Column("thread_id", sa.Integer, unique=True, primary_key=True, nullable=False))


def downgrade() -> None:
    op.drop_table("processedforumthread")
