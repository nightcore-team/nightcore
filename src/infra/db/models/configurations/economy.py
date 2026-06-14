from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
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
    )

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildeconomyconfig.guild_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    cost: Mapped[int] = mapped_column(Integer, nullable=False)


class GuildEconomyConfig(IdIntegerMixin, Base):  #
    """Economy configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )

    coin_name: Mapped[str | None] = mapped_column(String, nullable=True)
    economy_access_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    reward_bonus: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
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

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        if "economy_shop_items" in config:
            config["economy_shop_items"] = [
                GuildEconomyShopItem(**item)
                for item in config["economy_shop_items"]
            ]

        return config
