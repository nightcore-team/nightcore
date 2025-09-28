"""RoleRequestState model for the Nightcore bot database."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._enums import RoleRequestStateEnum
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class RoleRequestState(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    author_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    state: Mapped[RoleRequestStateEnum] = mapped_column(
        Enum(
            RoleRequestStateEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "idx_rr_guild_author_updated_desc",
            "guild_id",
            "author_id",
            text("updated_at DESC"),
            postgresql_concurrently=True,
        ),
        # Separate index to optimize queries filtering only by author_id
        Index(
            "idx_rr_author_updated_desc",
            "author_id",
            text("updated_at DESC"),
            postgresql_concurrently=True,
        ),
    )
