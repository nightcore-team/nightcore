"""add extrawallet bank account index

Revision ID: 3e7ea9a6cd7b
Revises: 9d004a16c046
Create Date: 2026-09-28 12:59:59.742438

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e7ea9a6cd7b'
down_revision: Union[str, Sequence[str], None] = '9d004a16c046'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # extrawallet.bank_account_id carried only a FK constraint, so every
    # read of a user's extra wallets was a sequential scan. That read is not
    # limited to the bank commands: selectinload(BankAccount.extra_wallets)
    # runs it on the shared user load path (user_load_all), and
    # create_extra_wallet scans for max(slot) on every creation.
    # deposit and bankaccount are already indexed by their unique
    # constraints, extrawallet was the only one missing.
    op.create_index('ix_extrawallet_bank_account_id', 'extrawallet', ['bank_account_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_extrawallet_bank_account_id', table_name='extrawallet')
