"""Color model for the Nightcore bot database."""

from typing import Any

from sqlalchemy import BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class Color(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint("guild_id", "role_id", name="ux_role_guild_color"),
    )

    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    @staticmethod
    def normalize_from_json(config: dict[str, Any]) -> dict[str, Any]:
        """Normalize the raw config payload."""
        # role_id comes as string from JSON
        if "role_id" in config and config["role_id"] is not None:
            config["role_id"] = int(config["role_id"])
        return config

    __version__ = 1
