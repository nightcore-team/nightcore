"""User model for the Nightcore bot database."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Integer,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class User(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint("guild_id", "user_id", name="ux_user_guild_user"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    coins: Mapped[int] = mapped_column(nullable=False, default=0)
    level: Mapped[int] = mapped_column(nullable=False, default=0)
    messages_count: Mapped[int] = mapped_column(
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
    battle_pass_level: Mapped[int] = mapped_column(nullable=False, default=0)
    battle_pass_points: Mapped[int] = mapped_column(nullable=False, default=0)
    inventory: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # type: ignore
