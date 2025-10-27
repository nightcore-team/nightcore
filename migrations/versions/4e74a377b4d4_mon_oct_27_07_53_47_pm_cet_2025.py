"""Mon Oct 27 07:53:47 PM CET 2025

Revision ID: 4e74a377b4d4
Revises: 3e3c7307f707
Create Date: 2025-10-27 19:53:48.607334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4e74a377b4d4'
down_revision: Union[str, Sequence[str], None] = '3e3c7307f707'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Спочатку видали дані (якщо вони є і не потрібні)
    # АБО конвертуй UUID -> TEXT -> BIGINT

    # Варіант 1: Якщо дані не важливі - просто очисти
    op.execute("DELETE FROM shoporderstate")

    # Тепер змінюй тип
    op.alter_column(
        'shoporderstate',
        'custom_id',
        existing_type=postgresql.UUID(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using='custom_id::text::bigint'  # <-- ЦЕ КЛЮЧОВЕ!
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Зворотня конвертація
    op.alter_column(
        'shoporderstate',
        'custom_id',
        existing_type=sa.BigInteger(),
        type_=postgresql.UUID(),
        existing_nullable=False,
        postgresql_using='custom_id::text::uuid'  # <-- Конвертація назад
    )