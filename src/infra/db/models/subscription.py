from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.utils._enums import GuildStatusEnum


class DiscordGuildORM(IdIntegerMixin, Base):
    """A discord guild that holds a Nightcore subscription."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False
    )
    is_whitelisted: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("false")
    )
    status: Mapped[GuildStatusEnum] = mapped_column(
        Enum(
            GuildStatusEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
    )
