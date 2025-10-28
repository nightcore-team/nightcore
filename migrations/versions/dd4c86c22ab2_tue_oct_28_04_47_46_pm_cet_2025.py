"""Tue Oct 28 04:47:46 PM CET 2025

Revision ID: dd4c86c22ab2
Revises: cea518fd4930
Create Date: 2025-10-28 16:47:47.534793

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd4c86c22ab2'
down_revision: Union[str, Sequence[str], None] = 'cea518fd4930'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Додаємо temp_coins_multiplier
    op.add_column('guildlevelsconfig', sa.Column('temp_coins_multiplier', sa.Float(), nullable=True))

    # Додаємо count_messages_type з default значенням
    op.add_column('guildlevelsconfig', sa.Column('count_messages_type', sa.String(), server_default=sa.text("'channel_only'"), nullable=False))

    # Заповнюємо NULL значення для base_exp_multiplier (default 1.0)
    op.execute("UPDATE guildlevelsconfig SET base_exp_multiplier = 1.0 WHERE base_exp_multiplier IS NULL")

    # Заповнюємо NULL значення для base_coins_multiplier (default 1.0)
    op.execute("UPDATE guildlevelsconfig SET base_coins_multiplier = 1.0 WHERE base_coins_multiplier IS NULL")

    # Тепер робимо колонки NOT NULL
    op.alter_column('guildlevelsconfig', 'base_exp_multiplier',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False)
    op.alter_column('guildlevelsconfig', 'base_coins_multiplier',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False)

    # Видаляємо стару колонку (typo: multipler → multiplier)
    op.drop_column('guildlevelsconfig', 'temp_coins_multipler')

    # Зміни для user таблиці
    op.alter_column('user', 'current_exp',
               existing_type=sa.BIGINT(),
               type_=sa.Float(),
               existing_nullable=False)
    op.alter_column('user', 'exp_to_level',
               existing_type=sa.BIGINT(),
               type_=sa.Float(),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('user', 'exp_to_level',
               existing_type=sa.Float(),
               type_=sa.BIGINT(),
               existing_nullable=False)
    op.alter_column('user', 'current_exp',
               existing_type=sa.Float(),
               type_=sa.BIGINT(),
               existing_nullable=False)
    op.add_column('guildlevelsconfig', sa.Column('temp_coins_multipler', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.alter_column('guildlevelsconfig', 'base_coins_multiplier',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True)
    op.alter_column('guildlevelsconfig', 'base_exp_multiplier',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True)
    op.drop_column('guildlevelsconfig', 'count_messages_type')
    op.drop_column('guildlevelsconfig', 'temp_coins_multiplier')