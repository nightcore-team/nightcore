"""Temporary tables models."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    Integer,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.utils._enums import MultiplierTypeEnum


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
    multiplier: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    duration: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "multiplier_type",
            name="ux_temp_multiplier_guild_type",
        ),
        CheckConstraint(
            "multiplier >= 0", name="ck_temp_multiplier_nonnegative"
        ),
        CheckConstraint("duration >= 0", name="ck_temp_duration_nonnegative"),
        Index(
            "ix_temp_economy_multipliers_guild_type_end_time",
            "guild_id",
            "multiplier_type",
        ),
        Index(
            "ix_temp_economy_multipliers_end_time",
            "end_time",
        ),
    )
