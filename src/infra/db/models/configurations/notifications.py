from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildNotificationsConfig(IdIntegerMixin, Base):  #
    """Notifications configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    notifications_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    notifications_for_moderation_channel_id: Mapped[int | None] = (
        mapped_column(BigInteger, nullable=True)
    )
    notifications_from_bot_channel_id: Mapped[int] = mapped_column(
        BigInteger, nullable=True
    )
