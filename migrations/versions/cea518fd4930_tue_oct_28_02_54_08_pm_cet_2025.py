"""Tue Oct 28 02:54:08 PM CET 2025

Revision ID: cea518fd4930
Revises: 4e74a377b4d4
Create Date: 2025-10-28 14:54:14.707552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'cea518fd4930'
down_revision: Union[str, Sequence[str], None] = '4e74a377b4d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Конвертуємо ARRAY в JSON з явним USING
    op.execute("""
        ALTER TABLE guildlevelsconfig
        ALTER COLUMN bonus_access_roles_ids
        TYPE JSON
        USING CASE
            WHEN bonus_access_roles_ids IS NULL THEN '{}'::json
            ELSE array_to_json(bonus_access_roles_ids)::json
        END
    """)

    # Встановлюємо NOT NULL і default
    op.alter_column(
        'guildlevelsconfig',
        'bonus_access_roles_ids',
        nullable=False,
        server_default=sa.text("'{}'::json")
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Конвертуємо JSON назад в ARRAY
    op.execute("""
        ALTER TABLE guildlevelsconfig
        ALTER COLUMN bonus_access_roles_ids
        TYPE BIGINT[]
        USING CASE
            WHEN bonus_access_roles_ids = '{}'::json THEN NULL
            ELSE ARRAY(SELECT json_array_elements_text(bonus_access_roles_ids)::bigint)
        END
    """)

    # Прибираємо NOT NULL
    op.alter_column(
        'guildlevelsconfig',
        'bonus_access_roles_ids',
        nullable=True
    )