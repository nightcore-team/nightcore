from typing import Any

from sqlalchemy import (
    BigInteger,
    Enum,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.infra.db.models.discord_webhook import DiscordWebhook
from src.utils._enums import MessageCountTypeEnum


class GuildLevel(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "level",
            name="uq_level_guild_level",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildlevelsconfig.guild_id", ondelete="CASCADE"),
        nullable=False,
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)


class GuildBonusRole(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "role_id",
            name="uq_bonus_guild_role",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildlevelsconfig.guild_id", ondelete="CASCADE"),
        nullable=False,
    )
    coins: Mapped[int] = mapped_column(Integer, nullable=False)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)


class GuildLevelsConfig(IdIntegerMixin, Base):  #
    """Level configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )

    count_messages_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    _level_notify_webhook_id: Mapped[int | None] = mapped_column(
        "level_notify_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    level_notify_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_level_notify_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    bonus_access_roles_ids: Mapped[list[GuildBonusRole]] = relationship(
        GuildBonusRole,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    level_roles: Mapped[list[GuildLevel]] = relationship(
        GuildLevel,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    count_messages_type: Mapped[MessageCountTypeEnum | None] = mapped_column(
        Enum(
            MessageCountTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=True,
        default=MessageCountTypeEnum.ALL,
    )

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        if "level_roles" in config:
            config["level_roles"] = [
                GuildLevel(**item) for item in config["level_roles"]
            ]

        if "bonus_access_roles_ids" in config:
            config["bonus_access_roles_ids"] = [
                GuildBonusRole(**item)
                for item in config["bonus_access_roles_ids"]
            ]

        return config
