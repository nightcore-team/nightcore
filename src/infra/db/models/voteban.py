"""TicketState model for the Nightcore bot database."""

from sqlalchemy import ARRAY, BigInteger, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import expression

from src.infra.db.models._enums import VoteBanStateEnum
from src.infra.db.models._mixins import (
    CreatedAtMixin,
    IdIntegerMixin,
    UpdatedAtMixin,
)
from src.infra.db.models.base import Base


class VoteBanState(IdIntegerMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str] = mapped_column(nullable=False)
    original_duration: Mapped[str] = mapped_column(nullable=False)
    duration: Mapped[int] = mapped_column(nullable=False)
    original_delete_messages_per: Mapped[str] = mapped_column(nullable=True)
    delete_messages_per: Mapped[int] = mapped_column(nullable=True)
    against_moderators_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    for_moderators_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    attachments_urls: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=True
    )

    state: Mapped[VoteBanStateEnum] = mapped_column(
        Enum(
            VoteBanStateEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
        default=VoteBanStateEnum.PENDING,
    )

    __table_args__ = (
        Index(
            "uq_vote_ban_guild_user_pending",
            "guild_id",
            "user_id",
            unique=True,
            postgresql_where=expression.column("state")
            == VoteBanStateEnum.PENDING.value,
        ),
        Index(
            "idx_vote_ban_guild_user_state",
            "guild_id",
            "user_id",
            "state",
        ),
    )
