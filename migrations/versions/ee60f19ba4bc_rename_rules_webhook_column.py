"""rename rules webhook column

Revision ID: ee60f19ba4bc
Revises: 525341db459a
Create Date: 2026-08-25 15:37:44.698680

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee60f19ba4bc'
down_revision: Union[str, Sequence[str], None] = '525341db459a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # The column was created with a copy-pasted name from the logging config.
    op.alter_column(
        "guildrulesconfig",
        "economy_log_webhook_id",
        new_column_name="rules_webhook_id",
    )
    op.execute(
        sa.text(
            "ALTER TABLE guildrulesconfig"
            " RENAME CONSTRAINT guildrulesconfig_economy_log_webhook_id_fkey"
            " TO guildrulesconfig_rules_webhook_id_fkey"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            "ALTER TABLE guildrulesconfig"
            " RENAME CONSTRAINT guildrulesconfig_rules_webhook_id_fkey"
            " TO guildrulesconfig_economy_log_webhook_id_fkey"
        )
    )
    op.alter_column(
        "guildrulesconfig",
        "rules_webhook_id",
        new_column_name="economy_log_webhook_id",
    )
