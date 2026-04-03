"""add_guild_forum_config

Revision ID: 75925089facf
Revises: caf7d09297b3
Create Date: 2026-04-03 19:30:51.674459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75925089facf'
down_revision: Union[str, Sequence[str], None] = 'caf7d09297b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("guildforumconfig", 
    sa.Column("guild_id", sa.BigInteger, nullable=False),
    sa.Column("section_id", sa.Integer, nullable=False),
    sa.Column("channel_id", sa.BigInteger, nullable=False),
    sa.Column("role_id", sa.BigInteger, nullable=False),
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('guild_id', "channel_id", "role_id", "section_id", name="uq_guild_channel_role_section")
    )


def downgrade() -> None:
    op.drop_table("guildforumconfig")
