"""TicketState model for the Nightcore bot database."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._enums import NotifyStateEnum
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class NotifyState(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    state: Mapped[NotifyStateEnum] = mapped_column(
        Enum(
            NotifyStateEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "idx_notify_guild_user_end_time_desc",
            "guild_id",
            "user_id",
            text("end_time DESC"),
        ),
    )
