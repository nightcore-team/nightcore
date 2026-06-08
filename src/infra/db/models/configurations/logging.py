from sqlalchemy import ARRAY, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildLoggingConfig(IdIntegerMixin, Base):  #
    """Logging configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    bans_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    clans_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    members_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    messages_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    voices_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    moderation_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    tickets_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    roles_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    channels_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    reactions_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    private_rooms_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    economy_log_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    message_log_ignoring_channels_ids: Mapped[list[int] | None] = (
        mapped_column(ARRAY(BigInteger), nullable=True)
    )
