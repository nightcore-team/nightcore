"""User model for the Nightcore bot database."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import CreatedAtMixin, IdIntegerMixin
from src.infra.db.models.badge import GlobalBadge, GuildBadge
from src.infra.db.models.base import Base
from src.infra.db.models.case import Case
from src.infra.db.models.color import Color
from src.infra.db.models.vip import VipStatus

if TYPE_CHECKING:
    from src.infra.db.models.bank import BankAccount

user_colors = Table(
    "user_colors",
    Base.metadata,
    Column("guild_id", BigInteger, nullable=False),
    Column("user_id", BigInteger, nullable=False),
    Column("color_id", Integer, ForeignKey("color.id", ondelete="CASCADE")),
    ForeignKeyConstraint(
        ["guild_id", "user_id"],
        ["user.guild_id", "user.user_id"],
        ondelete="CASCADE",
    ),
    PrimaryKeyConstraint("user_id", "color_id", "guild_id"),
)

if TYPE_CHECKING:
    from src.infra.db.models.casino import CasinoBet


class User(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint("guild_id", "user_id", name="ux_user_guild_user"),
        # the child tables point at (id, guild_id) rather than
        # (guild_id, user_id), so the guild a row belongs to can never drift
        # away from the guild of the user it references
        UniqueConstraint("id", "guild_id", name="ux_user_id_guild"),
        # Performance indexes for leaderboard queries
        Index("ix_user_guild_coins", "guild_id", text("coins DESC")),
        Index(
            "ix_user_guild_level_exp",
            "guild_id",
            text("level DESC"),
            text("current_exp DESC"),
        ),
        Index("ix_user_guild_voice", "guild_id", text("voice_activity DESC")),
        Index(
            "ix_user_guild_battlepass",
            "guild_id",
            text("battle_pass_level DESC"),
        ),
        Index(
            "ix_user_guild_messages", "guild_id", text("messages_count DESC")
        ),
    )

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    coins: Mapped[int] = mapped_column(nullable=False, default=0)
    rerolls: Mapped[int] = mapped_column(nullable=False, default=0)
    level: Mapped[int] = mapped_column(nullable=False, default=0)
    messages_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    sended_valentines: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    received_valentines: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    current_exp: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    exp_to_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    voice_activity: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    temp_voice_activity: Mapped["datetime | None"] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reward_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ticket_ban: Mapped[bool] = mapped_column(nullable=False, default=False)
    role_request_ban: Mapped[bool] = mapped_column(
        nullable=False, default=False
    )
    battle_pass_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    battle_pass_points: Mapped[int] = mapped_column(nullable=False, default=0)
    battle_pass_additional_reward_claimed_level: Mapped[int | None] = (
        mapped_column(Integer, nullable=True)
    )
    vip_statuses: Mapped[list["UserVipStatus"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    guild_badges: Mapped[list["UserGuildBadge"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    global_badges: Mapped[list["UserGlobalBadge"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    cases: Mapped[list["UserCase"]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    colors: Mapped[list[Color]] = relationship(
        secondary=user_colors,
        cascade="save-update, merge",
        passive_deletes=True,
    )
    casino_bets: Mapped[list["CasinoBet"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    bank_account: Mapped["BankAccount | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def get_case(self, case_id: int) -> Optional["UserCase"]:
        """Retrieves a case from the user's collection by its id."""

        for case in self.cases:
            if case.item.id == case_id:
                return case

    def get_color(self, color_id: int) -> Optional["Color"]:
        """Retrieves a color from the user's collection by its id."""
        for color in self.colors:
            if color.id == color_id:
                return color


class UserGuildBadge(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "badge_id",
            "user_id",
            "guild_id",
            name="ux_user_guild_badge",
        ),
        ForeignKeyConstraint(
            ["user_id", "guild_id"],
            ["user.id", "user.guild_id"],
            ondelete="CASCADE",
        ),
    )

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    badge_id: Mapped[int] = mapped_column(
        ForeignKey("guildbadge.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="guild_badges")
    badge: Mapped["GuildBadge"] = relationship()


class UserGlobalBadge(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="ux_user_global_badge"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    badge_id: Mapped[int] = mapped_column(
        ForeignKey("globalbadge.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="global_badges")
    badge: Mapped["GlobalBadge"] = relationship()


class UserVipStatus(IdIntegerMixin, CreatedAtMixin, Base):
    __table_args__ = (
        # a user may hold several VIPs, but only one of them is active at a
        # time, so the active one is unique per user and per guild
        Index(
            "ux_user_vip_active_guild_user",
            "guild_id",
            "user_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
        UniqueConstraint(
            "vip_id", "user_id", "guild_id", name="ux_user_vip_guild"
        ),
        ForeignKeyConstraint(
            ["user_id", "guild_id"],
            ["user.id", "user.guild_id"],
            ondelete="CASCADE",
        ),
    )

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    vip_id: Mapped[int] = mapped_column(
        ForeignKey("vipstatus.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=False, nullable=False)
    # None = permanent VIP status; otherwise the expire_vip task deletes the
    # row once the date passes, so a passed date never grants anything on
    # its own - the read paths filter on expires_at as well
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="vip_statuses")
    vip: Mapped["VipStatus"] = relationship()


class UserCase(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "case_id", "user_id", "guild_id", name="ux_user_case_guild_user"
        ),
        ForeignKeyConstraint(
            ["guild_id", "user_id"],
            ["user.guild_id", "user.user_id"],
            ondelete="CASCADE",
        ),
    )

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("case.id", ondelete="CASCADE"), primary_key=True
    )
    amount: Mapped[int] = mapped_column(default=1)
    item: Mapped["Case"] = relationship()
