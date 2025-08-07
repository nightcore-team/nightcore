"""User model for the Nightcore bot database."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models.base import Base
from src.infra.db.models.mixins import IdIntegerMixin


class User(IdIntegerMixin, Base):
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    coins: Mapped[float] = mapped_column(nullable=False, default=0.0)
    level: Mapped[int] = mapped_column(nullable=False, default=0)
    current_exp: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    exp_to_level: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    voice_activity: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    temp_voice_activity: Mapped["datetime | None"] = mapped_column(
        DateTime, nullable=True
    )
    reward_time: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    ticket_ban: Mapped[bool] = mapped_column(nullable=False, default=False)
    ban_role_request: Mapped[bool] = mapped_column(
        nullable=False, default=False
    )
    battle_pass_level: Mapped[int] = mapped_column(nullable=False, default=0)
    battle_pass_points: Mapped[float] = mapped_column(
        nullable=False, default=0.0
    )
    inventory: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # def __repr__(self):
    #     return f"<User user_id={self.user_id} guild_id={self.guild_id} coins={self.coins}>" # noqa: E501
