"""Punish model for the Nightcore bot database."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


# TODO: add original duration for infractions command
class Punish(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category: Mapped[str] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(nullable=True)
    duration: Mapped[int] = mapped_column(
        nullable=True
    )  # срок выдачи наказания
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # время окончания наказания
    time_now: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )  # время выдачи наказания

    __table_args__ = (
        Index(
            "ix_punish_guild_user_time_now", "guild_id", "user_id", "time_now"
        ),
    )
