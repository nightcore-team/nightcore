"""add_color_compensation

Revision ID: 388dd26ece6a
Revises: a21b9a0bb831
Create Date: 2026-02-01 19:10:23.843275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '388dd26ece6a'
down_revision: Union[str, Sequence[str], None] = 'a21b9a0bb831'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("guildeconomyconfig", sa.Column(
       "color_drop_compensation", sa.Integer, server_default=sa.text("0"), nullable=False
    ))


def downgrade() -> None:
    op.drop_column('guildeconomyconfig', 'color_drop_compensation')
