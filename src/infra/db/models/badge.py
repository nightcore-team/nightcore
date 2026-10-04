"""Badge model for the Nightcore bot database."""

from typing import Any

from sqlalchemy import BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildBadge(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint("guild_id", "name", name="ux_guild_badge_name"),
    )

    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    emoji_str: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        """Normalize the raw config payload."""
        return config

    __version__ = 1


class GlobalBadge(IdIntegerMixin, Base):
    __table_args__ = (UniqueConstraint("name", name="ux_global_badge_name"),)

    name: Mapped[str] = mapped_column(nullable=False)
    emoji_str: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        """Normalize the raw config payload."""
        return config

    __version__ = 1
