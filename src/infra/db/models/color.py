"""Color model for the Nightcore bot database."""

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
