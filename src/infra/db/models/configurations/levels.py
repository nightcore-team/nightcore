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
    level_notify_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
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
