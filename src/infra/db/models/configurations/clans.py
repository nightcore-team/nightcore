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


class GuildClanShopItem(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "name",
            name="uq_guild_name",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("guildclansconfig.guild_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    cost: Mapped[int] = mapped_column(Integer, nullable=False)


class GuildClansConfig(IdIntegerMixin, Base):
    """Clans configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    create_clan_channel_category_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    clan_payday_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
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
