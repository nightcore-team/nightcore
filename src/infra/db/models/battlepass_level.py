"""BattlepassLevel model for the Nightcore bot database."""

from typing import Any

from sqlalchemy import JSON, BigInteger, UniqueConstraint, text
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
    additional_reward: Mapped[BattlepassRewardAnnot] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        server_default=text("'[]'::json"),
    )

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        """Normalize the raw config payload."""
        # Ensure numeric fields are int
        for field in ("level", "exp_required"):
            if field in config and config[field] is not None:
                config[field] = int(config[field])

        # reward and additional_reward are dicts
        for field in ("reward", "additional_reward"):
            if field in config and config[field] is not None:
                reward = config[field]
                if isinstance(reward, dict):
                    for rf in ("drop_id", "amount", "type"):
                        if rf in reward and reward[rf] is not None:
                            reward[rf] = int(reward[rf])  # type: ignore
        return config

    __version__ = 1
