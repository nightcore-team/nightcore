"""Guild economy configuration models."""

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


class GuildEconomyShopItem(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "name",
            name="uq_economy_guild_name",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint("cost >= 0", name="ck_economy_shop_cost_nonnegative"),
    )

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildeconomyconfig.guild_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    cost: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )


class GuildRewardBonus(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "role_id",
            name="uq_reward_bonus_guild",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "coins >= 0", name="ck_reward_bonus_coins_nonnegative"
        ),
    )

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildeconomyconfig.guild_id", ondelete="CASCADE"),
        nullable=False,
    )
    coins: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)


class GuildEconomyConfig(IdIntegerMixin, Base):  #
    """Economy configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )

    coin_name: Mapped[str | None] = mapped_column(String, nullable=True)
    economy_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    base_reward_bonus: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    reward_bonuses: Mapped[list[GuildRewardBonus]] = relationship(
        GuildRewardBonus,
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    economy_shop_buy_ping_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    economy_shop_items: Mapped[list[GuildEconomyShopItem]] = relationship(
        GuildEconomyShopItem,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    casino_multiplayer_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    color_drop_compensation: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    __table_args__ = (
        CheckConstraint(
            "base_reward_bonus >= 0",
            name="ck_economy_base_reward_nonnegative",
        ),
        CheckConstraint(
            "color_drop_compensation >= 0",
            name="ck_economy_color_comp_nonnegative",
        ),
    )

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:  # noqa: D102
        if "economy_shop_items" in config:
            shop_items: list[Any] = config["economy_shop_items"] or []
            config["economy_shop_items"] = [
                GuildEconomyShopItem(**item) for item in shop_items
            ]

        if "reward_bonuses" in config:
            reward_bonuses: list[Any] = config["reward_bonuses"] or []
            config["reward_bonuses"] = [
                GuildRewardBonus(**item) for item in reward_bonuses
            ]

        return config

    __version__ = 1

    @staticmethod
    def patch_revision(data: dict[str, Any]) -> dict[str, Any]:
        """Apply a patch to a config revision data dict."""
        ...
