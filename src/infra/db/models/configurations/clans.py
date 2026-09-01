"""Guild clans configuration models."""

from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.infra.db.models.discord_webhook import DiscordWebhook


class GuildClanShopItem(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "name",
            name="uq_guild_name",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("cost >= 0", name="ck_clan_shop_cost_nonnegative"),
    )

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildclansconfig.guild_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    cost: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )


class GuildClansConfig(IdIntegerMixin, Base):
    """Clans configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    create_clan_channel_category_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    _clan_payday_webhook_id: Mapped[int | None] = mapped_column(
        "clan_payday_webhook_id",
        ForeignKey("discordwebhook.id", ondelete="SET NULL"),
        nullable=True,
    )
    clan_payday_webhook: Mapped[DiscordWebhook | None] = relationship(
        DiscordWebhook,
        foreign_keys=[_clan_payday_webhook_id],
        lazy="selectin",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    clan_shop_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    clan_shop_items: Mapped[list[GuildClanShopItem]] = relationship(
        GuildClanShopItem,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    clans_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    clan_buy_ping_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    clan_reputation_per_payday: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    base_exp_multiplier: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    clan_improvements: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, default=list
    )

    __table_args__ = (
        CheckConstraint(
            "clan_reputation_per_payday >= 0",
            name="ck_clan_rep_nonnegative",
        ),
        CheckConstraint(
            "base_exp_multiplier >= 0",
            name="ck_clan_exp_mult_nonnegative",
        ),
    )

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        """Normalize clan shop items in the raw config payload."""
        if "clan_shop_items" in config:
            shop_items: list[Any] = config["clan_shop_items"] or []
            config["clan_shop_items"] = [
                GuildClanShopItem(**item) for item in shop_items
            ]

        if "clan_payday_webhook" in config:
            webhook = config["clan_payday_webhook"]
            config["clan_payday_webhook"] = (
                DiscordWebhook(**webhook) if webhook is not None else None
            )

        return config

    __version__ = 1

    @staticmethod
    def patch_revision(data: dict[str, Any]) -> dict[str, Any]:
        """Apply a patch to a config revision data dict."""
        ...
