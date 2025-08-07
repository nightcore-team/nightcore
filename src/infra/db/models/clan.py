"""Clan model for the Nightcore bot database."""

from sqlalchemy import ARRAY, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models.base import Base
from src.infra.db.models.mixins import CreatedAtMixin, IdIntegerMixin


class Clan(IdIntegerMixin, Base, CreatedAtMixin):
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    leader_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deputies: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=False, default=list
    )  # Array of deputy IDs
    coins: Mapped[float] = mapped_column(nullable=False, default=0.0)
    current_exp: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    exp_to_level: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    level: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    ## payday for clan
    max_deputies: Mapped[int] = mapped_column(nullable=False, default=0)
    max_members: Mapped[int] = mapped_column(nullable=False, default=0)
    payday_multipler: Mapped[int] = mapped_column(nullable=False, default=1)
    invite_message: Mapped[str | None] = mapped_column(nullable=True)
