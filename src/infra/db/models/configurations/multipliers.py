from sqlalchemy import BigInteger, Float, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildMultipliersConfig(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    base_exp_multiplier: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    temp_exp_multiplier: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    base_coins_multiplier: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    temp_coins_multiplier: Mapped[int | None] = mapped_column(
        Float, nullable=True
    )
    base_battlepass_multiplier: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    temp_battlepass_multiplier: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
