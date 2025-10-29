"""Fix user inventory structure

Revision ID: de705820b328
Revises: 942ff738079f
Create Date: 2025-10-29 21:32:40.750973
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'de705820b328'
down_revision: Union[str, Sequence[str], None] = '942ff738079f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.execute("""
        UPDATE "user"
        SET inventory = jsonb_build_object(
            'cases', COALESCE(inventory::jsonb->'cases', '{}'::jsonb),
            'colors', COALESCE(inventory::jsonb->'colors', '{}'::jsonb)
        )::json
    """)

    # 3. Змінюємо server_default для нових записів
    op.alter_column(
        'user',
        'inventory',
        existing_type=sa.JSON(),
        nullable=False,
        server_default=sa.text("'{\"cases\": {}, \"colors\": {}}'::json")
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Повертаємо старий server_default
    op.alter_column(
        'user',
        'inventory',
        existing_type=sa.JSON(),
        nullable=False,
        server_default=sa.text("'{}'::json")
    )