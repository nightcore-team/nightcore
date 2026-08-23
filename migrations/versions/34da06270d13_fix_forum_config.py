"""fix_forum_config

Revision ID: 34da06270d13
Revises: 3e650f60e04b
Create Date: 2026-08-23 18:13:03.303687

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34da06270d13'
down_revision: Union[str, Sequence[str], None] = '3e650f60e04b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('guildforumconfig', 'prefix_id',
               existing_type=sa.BOOLEAN(),
               type_=sa.Integer(),
               existing_nullable=True,
               postgresql_using="prefix_id::integer")

    op.execute(sa.text("UPDATE guildforumconfig SET prefix_id = NULL"))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('guildforumconfig', 'prefix_id',
               existing_type=sa.Integer(),
               type_=sa.BOOLEAN(),
               existing_nullable=True,
               postgresql_using="prefix_id::boolean")
