"""point uservipstatus.user_id at the user primary key

Revision ID: c3d90b6a4f18
Revises: a7c1f4e92b60
Create Date: 2026-09-28 15:31:08.664201

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d90b6a4f18'
down_revision: Union[str, Sequence[str], None] = 'a7c1f4e92b60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# uservipstatus held the discord snowflake, while bankaccount - the other
# half of the economy - held user.id. Two names for the same user in two
# tables, so the two could never be joined: close_out_deposits_before_rate_change
# matched BankAccount.user_id against UserVipStatus.user_id and found
# nothing, and accrue_deposit_interest_if_due was handed a surrogate id by
# every bank command, so the VIP deposit bonus never resolved.
#
# the old FK guarantees a matching user row for every VIP row, so this join
# always finds a target, and (guild_id, user_id) is unique on user, so no two
# rows can collapse onto the same surrogate.
_REWRITE_TO_USER_PK = """
UPDATE uservipstatus AS vip
SET user_id = u.id
FROM "user" AS u
WHERE u.guild_id = vip.guild_id
  AND u.user_id = vip.user_id
"""

_REWRITE_TO_SNOWFLAKE = """
UPDATE uservipstatus AS vip
SET user_id = u.user_id
FROM "user" AS u
WHERE u.id = vip.user_id
  AND u.guild_id = vip.guild_id
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        'uservipstatus_guild_id_user_id_fkey',
        'uservipstatus',
        type_='foreignkey',
    )

    op.execute(_REWRITE_TO_USER_PK)

    # (user_id, guild_id) still belongs to one user, so the row keeps its
    # guild, but it now points at the row itself instead of at the discord id
    op.create_unique_constraint(
        'ux_user_id_guild',
        'user',
        ['id', 'guild_id'],
    )

    op.create_foreign_key(
        'fk_uservipstatus_user_id_guild_id',
        'uservipstatus',
        'user',
        ['user_id', 'guild_id'],
        ['id', 'guild_id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'fk_uservipstatus_user_id_guild_id',
        'uservipstatus',
        type_='foreignkey',
    )

    op.execute(_REWRITE_TO_SNOWFLAKE)

    op.drop_constraint('ux_user_id_guild', 'user', type_='unique')

    op.create_foreign_key(
        'uservipstatus_guild_id_user_id_fkey',
        'uservipstatus',
        'user',
        ['guild_id', 'user_id'],
        ['guild_id', 'user_id'],
        ondelete='CASCADE',
    )
