from typing import Any

from sqlalchemy import ARRAY, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.infra.db.models.discord_webhook import DiscordWebhook


class GuildLoggingConfig(IdIntegerMixin, Base):  #
    """Logging configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    _bans_log_webhook_id: Mapped[int | None] = mapped_column(
        "bans_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    bans_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_bans_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _clans_log_webhook_id: Mapped[int | None] = mapped_column(
        "clans_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    clans_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_clans_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _members_log_webhook_id: Mapped[int | None] = mapped_column(
        "members_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    members_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_members_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _messages_log_webhook_id: Mapped[int | None] = mapped_column(
        "messages_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    messages_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_messages_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _voices_log_webhook_id: Mapped[int | None] = mapped_column(
        "voices_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    voices_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_voices_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _moderation_log_webhook_id: Mapped[int | None] = mapped_column(
        "moderation_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    moderation_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_moderation_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _tickets_log_webhook_id: Mapped[int | None] = mapped_column(
        "tickets_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    tickets_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_tickets_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _roles_log_webhook_id: Mapped[int | None] = mapped_column(
        "roles_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    roles_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_roles_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _channels_log_webhook_id: Mapped[int | None] = mapped_column(
        "channels_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    channels_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_channels_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _reactions_log_webhook_id: Mapped[int | None] = mapped_column(
        "reactions_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    reactions_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_reactions_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _private_rooms_log_webhook_id: Mapped[int | None] = mapped_column(
        "private_rooms_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    private_rooms_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_private_rooms_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _economy_log_webhook_id: Mapped[int | None] = mapped_column(
        "economy_log_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    economy_log_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_economy_log_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    message_log_ignoring_channels_ids: Mapped[list[int] | None] = (
        mapped_column(ARRAY(BigInteger), nullable=True)
    )

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        for k, v in config.items():
            if k.endswith("_webhook"):
                config[k] = DiscordWebhook(**v)

        return config
