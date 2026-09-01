"""PrivateRoomState model for the Nightcore bot database."""

from sqlalchemy import BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class PrivateRoomState(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "guild_id", "user_id", name="ux_private_room_guild_user"
        ),
    )

    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
