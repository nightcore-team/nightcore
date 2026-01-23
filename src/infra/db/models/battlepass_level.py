"""BattlepassLevel model for the Nightcore bot database."""

from sqlalchemy import JSON, BigInteger, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models import Base
from src.infra.db.models._annot import BattlepassRewardAnnot
from src.infra.db.models._mixins import IdIntegerMixin


class BattlepassLevel(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "level", "guild_id", name="ux_level_guild_battlepasslevel"
        ),
    )

    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    level: Mapped[int] = mapped_column(nullable=False)
    exp_required: Mapped[int] = mapped_column(nullable=False)
    reward: Mapped[BattlepassRewardAnnot] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'[]'::json"),
    )
