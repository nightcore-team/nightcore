"""Punish model for the Nightcore bot database."""

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class Punish(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    used_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(nullable=True)
    duration: Mapped[str] = mapped_column(
        nullable=True
    )  # срок выдачи наказания
    end_time: Mapped[int] = mapped_column(
        nullable=True
    )  # время окончания наказания
    time_now: Mapped[int] = mapped_column(
        nullable=True
    )  # время выдачи наказания
