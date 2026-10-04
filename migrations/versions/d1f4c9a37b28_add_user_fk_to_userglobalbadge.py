"""add user fk to userglobalbadge

Revision ID: d1f4c9a37b28
Revises: bc06aaa66425
Create Date: 2026-10-04 21:30:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1f4c9a37b28"
down_revision: str | Sequence[str] | None = "bc06aaa66425"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_foreign_key(
        "fk_userglobalbadge_user_id",
        "userglobalbadge",
        "user",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_userglobalbadge_user_id", "userglobalbadge", type_="foreignkey"
    )
