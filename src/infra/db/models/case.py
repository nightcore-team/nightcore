"""Case model for the Nightcore bot database."""

import random

from sqlalchemy import JSON, BigInteger, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._annot import CaseDropAnnot
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class Case(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint("guild_id", "name", name="ux_name_guild_case"),
    )

    name: Mapped[str] = mapped_column(nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    drop: Mapped[list[CaseDropAnnot]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )

    def open(self, amount: int = 1) -> list[CaseDropAnnot | None]:
        """Open case and get reward."""

        if not self.drop:
            return [None] * amount

        chances = [drop["chance"] for drop in self.drop]

        selected_indices = random.choices(
            range(len(self.drop)), weights=chances, k=amount
        )

        return [self.drop[i] for i in selected_indices]
