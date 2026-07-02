from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.infra.db.models.discord_webhook import DiscordWebhook


class GuildNotificationsConfig(IdIntegerMixin, Base):  #
    """Notifications configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    notifications_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    _notifications_for_moderation_webhook_id: Mapped[int | None] = (
        mapped_column(
            "notifications_for_moderation_webhook_id",
            ForeignKey("discordwebhook.id", ondelete="SET NULL"),
            nullable=True,
        )
    )
    notifications_for_moderation_webhook: Mapped[DiscordWebhook | None] = (
        relationship(
            DiscordWebhook,
            foreign_keys=[_notifications_for_moderation_webhook_id],
            lazy="selectin",
            cascade="all, delete-orphan",
            single_parent=True,
        )
    )
    _notifications_from_bot_webhook_id: Mapped[int | None] = mapped_column(
        "notifications_from_bot_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    notifications_from_bot_webhook: Mapped[DiscordWebhook | None] = (
        relationship(
            DiscordWebhook,
            foreign_keys=[_notifications_from_bot_webhook_id],
            lazy="selectin",
            cascade="all, delete-orphan",
            single_parent=True,
        )
    )
