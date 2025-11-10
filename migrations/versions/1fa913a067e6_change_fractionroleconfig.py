""" change fractionroleconfig

Revision ID: 1fa913a067e6
Revises: b0304e52bb0d
Create Date: 2025-11-10 20:08:33.908922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1fa913a067e6'
down_revision: Union[str, Sequence[str], None] = 'b0304e52bb0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # ✅ Конвертація ARRAY → JSON з явним USING
    op.execute("""
        ALTER TABLE guildmoderationconfig
        ALTER COLUMN fraction_roles_access_roles_ids
        TYPE JSON
        USING fraction_roles_access_roles_ids::text::json
    """)

    # ✅ Встановлюємо server_default
    op.alter_column(
        'guildmoderationconfig',
        'fraction_roles_access_roles_ids',
        server_default=sa.text("'{}'::json"),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # ✅ Повернення JSON → ARRAY
    op.execute("""
        ALTER TABLE guildmoderationconfig
        ALTER COLUMN fraction_roles_access_roles_ids
        TYPE BIGINT[]
        USING ARRAY[]::BIGINT[]
    """)

    # ✅ Видаляємо server_default
    op.alter_column(
        'guildmoderationconfig',
        'fraction_roles_access_roles_ids',
        server_default=None,
        existing_nullable=False,
    )