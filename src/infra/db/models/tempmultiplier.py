"""Temporary tables models."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._enums import MultiplierTypeEnum
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class TempEconomyMultiplier(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    multiplier_type: Mapped[MultiplierTypeEnum] = mapped_column(
        Enum(
            MultiplierTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )
    multiplier: Mapped[int] = mapped_column(nullable=False)
    duration: Mapped[int] = mapped_column(nullable=False)
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "multiplier_type",
            name="ux_temp_multiplier_guild_type",
        ),
        Index(
            "ix_temp_economy_multipliers_guild_type_end_time",
            "guild_id",
            "multiplier_type",
            "end_time",
        ),
    )
