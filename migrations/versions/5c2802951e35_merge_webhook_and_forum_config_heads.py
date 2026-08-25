"""merge webhook and forum config heads

Revision ID: 5c2802951e35
Revises: ee60f19ba4bc, 34da06270d13
Create Date: 2026-08-25 17:20:16.808242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c2802951e35'
down_revision: Union[str, Sequence[str], None] = ('ee60f19ba4bc', '34da06270d13')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
