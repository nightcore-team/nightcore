"""TicketState model for the Nightcore bot database."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._enums import TicketStateEnum
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class TicketState(IdIntegerMixin, Base):
    ticket_number: Mapped[int] = mapped_column(Integer, nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    author_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    state: Mapped[TicketStateEnum] = mapped_column(
        Enum(
            TicketStateEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
