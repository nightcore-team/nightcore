"""Rainbow role model for the Nightcore bot database."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.utils._enums import RainbowColorChangeTypeEnum


class RainbowRole(IdIntegerMixin, Base):
    """A single rainbow role per guild."""

    __table_args__ = (UniqueConstraint("guild_id", name="ux_guild_rainbow"),)

    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    change_type: Mapped[RainbowColorChangeTypeEnum] = mapped_column(
        Enum(
            RainbowColorChangeTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
        default=RainbowColorChangeTypeEnum.OFFSET,
    )
    next_change_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
