"""Rainbow role model for the Nightcore bot database."""

from sqlalchemy import BigInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class RainbowRole(IdIntegerMixin, Base):
    """A single rainbow role per guild."""

    __table_args__ = (UniqueConstraint("guild_id", name="ux_guild_rainbow"),)

    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
