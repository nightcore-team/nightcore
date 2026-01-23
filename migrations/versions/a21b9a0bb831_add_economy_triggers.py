"""add_economy_triggers

Revision ID: a21b9a0bb831
Revises: 7fedbff7e42f
Create Date: 2026-01-23 22:28:09.801437

"""
from typing import Sequence, Union

from sqlalchemy import text

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a21b9a0bb831'
down_revision: Union[str, Sequence[str], None] = '7fedbff7e42f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open("migrations/structure.sql") as file:
        query = text(file.read())

    op.execute(query)


def downgrade() -> None:
    with open("migrations/drop_structure.sql") as file:
        query = text(file.read())

    op.execute(query)
