from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildPrivateChannelsConfig(IdIntegerMixin, Base):
    """Private channels configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    private_rooms_create_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
