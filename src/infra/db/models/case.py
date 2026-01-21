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

    def open(self) -> CaseDropAnnot | None:
        """Open case and get reward."""

        if not self.drop:
            return None

        chances = [drop["chance"] for drop in self.drop]

        selected_index = random.choices(
            range(len(self.drop)), weights=chances, k=1
        )[0]

        return self.drop[selected_index]
