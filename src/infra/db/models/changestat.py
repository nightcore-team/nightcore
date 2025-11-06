"""Moderation changestat model for the Nightcore bot database."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._enums import ChangeStatTypeEnum
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class ChangeStat(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[ChangeStatTypeEnum] = mapped_column(
        Enum(
            ChangeStatTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )
    time_now: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_changestats_guild_id_moderator_id_time_now",
            "guild_id",
            "moderator_id",
            "time_now",
        ),
    )
