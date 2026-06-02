from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildTicketsConfig(IdIntegerMixin, Base):
    """Tickets configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    tickets_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    new_tickets_category_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    closed_tickets_category_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    create_ticket_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    pinned_tickets_category_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    create_ticket_ping_role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
