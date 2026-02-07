"""User model for the Nightcore bot database."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    PrimaryKeyConstraint,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.infra.db.models.case import Case
from src.infra.db.models.color import Color

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
    )

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    coins: Mapped[int] = mapped_column(nullable=False, default=0)
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
    cases: Mapped[list["UserCase"]] = relationship(
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    colors: Mapped[list[Color]] = relationship(
        lazy="selectin",
        secondary=user_colors,
        cascade="save-update, merge",
        passive_deletes=True,
    )
    casino_bets: Mapped[list["CasinoBet"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
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


class UserCase(Base):
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
    id: Mapped[int] = mapped_column(
        autoincrement=True, nullable=False, primary_key=True
    )
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("case.id", ondelete="CASCADE"), primary_key=True
    )
    amount: Mapped[int] = mapped_column(default=1)
    item: Mapped["Case"] = relationship(lazy="selectin")
