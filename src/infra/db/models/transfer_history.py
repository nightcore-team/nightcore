"""User model for the Nightcore bot database."""

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import CreatedAtMixin, IdIntegerMixin
from src.infra.db.models.base import Base


class TransferHistory(Base, IdIntegerMixin, CreatedAtMixin):
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    receiver_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False, default=0)
