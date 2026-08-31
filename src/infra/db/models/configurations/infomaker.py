"""Guild infomaker configuration model."""

from typing import Any

from sqlalchemy import ARRAY, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.infra.db.models.discord_webhook import DiscordWebhook


class GuildInfomakerConfig(IdIntegerMixin, Base):
    """Infomaker configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    admins_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    leaders_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    _admins_roles_logging_webhook_id: Mapped[int | None] = mapped_column(
        "admins_roles_logging_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    admins_roles_logging_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_admins_roles_logging_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    _leaders_roles_logging_webhook_id: Mapped[int | None] = mapped_column(
        "leaders_roles_logging_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    leaders_roles_logging_webhook: Mapped[DiscordWebhook | None] = (
        relationship(
            DiscordWebhook,
            foreign_keys=[_leaders_roles_logging_webhook_id],
            lazy="selectin",
            cascade="all, delete-orphan",
            single_parent=True,
        )
    )

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        """Normalize admin roles logging webhook in the raw payload."""
        if "admins_roles_logging_webhook" in config:
            admins_webhook = config["admins_roles_logging_webhook"]
            config["admins_roles_logging_webhook"] = (
                DiscordWebhook(**admins_webhook)
                if admins_webhook is not None
                else None
            )

        if "leaders_roles_logging_webhook" in config:
            leaders_webhook = config["leaders_roles_logging_webhook"]
            config["leaders_roles_logging_webhook"] = (
                DiscordWebhook(**leaders_webhook)
                if leaders_webhook is not None
                else None
            )

        return config

    __version__ = 1

    @staticmethod
    def patch_revision(data: dict[str, Any]) -> dict[str, Any]:
        """Apply a patch to a config revision data dict."""
        ...
