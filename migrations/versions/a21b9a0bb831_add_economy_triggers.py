"""add_economy_triggers

Revision ID: a21b9a0bb831
Revises: bc10cf97b36d
Create Date: 2026-01-23 22:28:09.801437

"""
from typing import Sequence, Union

from sqlalchemy import text

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a21b9a0bb831'
down_revision: Union[str, Sequence[str], None] = 'bc10cf97b36d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with open("migrations/sql/economy_triggers.sql") as file:
        sql = file.read()

    commands = sql.split("\n\n")

    for command in commands:
        op.execute(text(command))



def downgrade() -> None:
    with open("migrations/sql/drop_economy_triggers.sql") as file:
        sql = file.read()

    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
        op.execute(text(stmt))
