"""BattlepassLevel model for the Nightcore bot database."""

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Integer,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._annot import BattlepassRewardAnnot
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class BattlepassLevel(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "level",
            "guild_id",
            deferrable=True,
            initially="DEFERRED",
            name="ux_level_guild_battlepasslevel",
        ),
        CheckConstraint("level >= 0", name="ck_battlepass_level_nonnegative"),
        CheckConstraint(
            "exp_required >= 0", name="ck_battlepass_exp_required_nonnegative"
        ),
    )

    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    level: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    exp_required: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    reward: Mapped[BattlepassRewardAnnot] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'[]'::json"),
    )
