"""empty message

Revision ID: 1e91b387214b
Revises: 70a2b7a2986a
Create Date: 2026-02-22 03:32:21.107559

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e91b387214b'
down_revision: Union[str, Sequence[str], None] = '70a2b7a2986a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with open("migrations/sql/pg_trgm_extension.sql") as file:
        sql = file.read()

    commands = sql.split("\n\n")

    for command in commands:
        op.execute(sa.text(command))



def downgrade() -> None:
    with open("migrations/sql/drop_pg_trgm_extension.sql") as file:
        sql = file.read()

    for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
        op.execute(sa.text(stmt))