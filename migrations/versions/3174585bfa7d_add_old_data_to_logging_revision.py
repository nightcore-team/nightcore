"""add old data to logging revision

Revision ID: 3174585bfa7d
Revises: 5c2802951e35
Create Date: 2026-08-25 17:47:16.884561

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3174585bfa7d'
down_revision: Union[str, Sequence[str], None] = '5c2802951e35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "loggingrevision",
        sa.Column(
            "old_data",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("loggingrevision", "old_data")
