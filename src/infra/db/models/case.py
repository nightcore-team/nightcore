"""Case model for the Nightcore bot database."""

import random

from sqlalchemy import JSON, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._annot import CaseDropAnnot
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class Case(IdIntegerMixin, Base):
    name: Mapped[str] = mapped_column(nullable=False)
    drop: Mapped[list[CaseDropAnnot]] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::json")
    )

    def open(self) -> CaseDropAnnot:
        """Open case and get reward."""

        if not self.drop:
            raise ValueError("Case has no drops configured")

        chances = [drop["chance"] for drop in self.drop]

        selected_index = random.choices(
            range(len(self.drop)), weights=chances, k=1
        )[0]

        return self.drop[selected_index]
