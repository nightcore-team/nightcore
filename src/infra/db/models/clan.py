"""Clan model for the Nightcore bot database."""

from sqlalchemy import (
    BigInteger,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    and_,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._enums import ClanMemberRoleEnum
from src.infra.db.models._mixins import CreatedAtMixin, IdIntegerMixin
from src.infra.db.models.base import Base


class Clan(IdIntegerMixin, Base, CreatedAtMixin):
    # Discord context
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    role_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # Discord role for the clan

    # Economy & progression
    coins: Mapped[int] = mapped_column(nullable=False, default=0)
    current_exp: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    exp_to_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Limits and config
    max_deputies: Mapped[int] = mapped_column(nullable=False, default=1)
    max_members: Mapped[int] = mapped_column(nullable=False, default=10)
    payday_multipler: Mapped[int] = mapped_column(nullable=False, default=1)
    invite_message: Mapped[str | None] = mapped_column(nullable=True)

    # channel
    clan_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, unique=True
    )

    members: Mapped[list["ClanMember"]] = relationship(
        back_populates="clan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
        order_by="ClanMember.role",
    )

    leader: Mapped["ClanMember"] = relationship(
        primaryjoin=lambda: and_(
            Clan.id == ClanMember.clan_id,
            ClanMember.role == ClanMemberRoleEnum.LEADER,
        ),
        viewonly=True,
        uselist=False,
        lazy="selectin",
    )

    deputies: Mapped[list["ClanMember"]] = relationship(
        primaryjoin=lambda: and_(
            Clan.id == ClanMember.clan_id,
            ClanMember.role == ClanMemberRoleEnum.DEPUTY,
        ),
        viewonly=True,
        lazy="selectin",
        order_by="ClanMember.id",
    )

    __table_args__ = (
        # уникальное название клана в пределах гильдии
        UniqueConstraint("guild_id", "name", name="uq_clan_guild_name"),
    )


class ClanMember(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    clan_id: Mapped[int] = mapped_column(
        ForeignKey("clan.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )

    # Role inside the clan
    role: Mapped[ClanMemberRoleEnum] = mapped_column(
        Enum(
            ClanMemberRoleEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
        default=ClanMemberRoleEnum.MEMBER,
    )

    clan: Mapped["Clan"] = relationship(back_populates="members")

    __table_args__ = (
        # uniq user per clan in guild
        UniqueConstraint("guild_id", "user_id", name="uq_member_guild_user"),
        # one role per clan
        Index("ix_clan_members_clan_role", "clan_id", "role"),
        # one leader per clan
        Index(
            "uq_one_leader_per_clan",
            "clan_id",
            unique=True,
            postgresql_where=text("role = 'leader'"),
        ),
    )
