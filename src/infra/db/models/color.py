"""Color model for the Nightcore bot database."""

from sqlalchemy import JSON, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._annot import CaseDropAnnot
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class Case(IdIntegerMixin, Base):
    name: Mapped[str] = mapped_column(nullable=False)
    drop: Mapped[CaseDropAnnot] = mapped_column(
        JSON, nullable=False, default=dict, server_default=text("'{}'::json")
    )
