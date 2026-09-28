"""enforce a single active vip status per user

Revision ID: a7c1f4e92b60
Revises: 3e7ea9a6cd7b
Create Date: 2026-09-28 15:02:41.118904

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c1f4e92b60'
down_revision: Union[str, Sequence[str], None] = '3e7ea9a6cd7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# keep the row that was activated last, so the user does not silently lose
# the VIP they are actually wearing
_DROP_EXTRA_ACTIVE = """
UPDATE uservipstatus AS keep
SET is_active = false
WHERE keep.id IN (
    SELECT id
    FROM (
        SELECT id, row_number() OVER (
            PARTITION BY guild_id, user_id ORDER BY created_at DESC, id DESC
        ) AS rn
        FROM uservipstatus
        WHERE is_active = true
    ) AS ranked
    WHERE ranked.rn > 1
)
"""


def upgrade() -> None:
    """Upgrade schema."""
    # a user can hold several VIPs but only one of them is active, and
    # ix_user_vip_active_guild_user was never unique, so nothing stopped a
    # second VIP from being activated as well.
    op.execute(_DROP_EXTRA_ACTIVE)

    op.drop_index('ix_user_vip_active_guild_user', table_name='uservipstatus')

    # ux_user_active_vip_guild (vip_id, user_id, is_active) is both redundant
    # and wrong here: ux_user_vip_guild already allows a single row per user
    # and vip, so the boolean adds nothing, while the unique pair it does
    # allow - one active and one inactive row for the same vip - can never be
    # reached and a partial unique index says what we actually mean.
    op.drop_constraint(
        'ux_user_active_vip_guild',
        'uservipstatus',
        type_='unique',
    )

    op.create_index(
        'ux_user_vip_active_guild_user',
        'uservipstatus',
        ['guild_id', 'user_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ux_user_vip_active_guild_user', table_name='uservipstatus'
    )

    op.create_index(
        'ix_user_vip_active_guild_user',
        'uservipstatus',
        ['guild_id', 'user_id'],
        unique=False,
        postgresql_where=sa.text('is_active = true'),
    )

    op.create_unique_constraint(
        'ux_user_active_vip_guild',
        'uservipstatus',
        ['vip_id', 'user_id', 'is_active'],
    )
