"""User model for the Nightcore bot database."""

from sqlalchemy import BigInteger, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import CreatedAtMixin, IdIntegerMixin
from src.infra.db.models.base import Base


class TransferHistory(Base, IdIntegerMixin, CreatedAtMixin):
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    receiver_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False, default=0)

    __table_args__ = (
        # Indexes for transfer history queries
        Index(
            "ix_transfer_guild_sender_created",
            "guild_id",
            "user_id",
            text("created_at DESC"),
        ),
        Index(
            "ix_transfer_guild_receiver_created",
            "guild_id",
            "receiver_id",
            text("created_at DESC"),
        ),
    )
