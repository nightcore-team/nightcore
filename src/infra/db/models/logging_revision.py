"""LoggingRevision model for the Nightcore bot database."""

from typing import Any

from sqlalchemy import JSON, BigInteger, Enum, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import UpdatedAtMixin
from src.infra.db.models.base import Base
from src.infra.db.models.clan import CreatedAtMixin
from src.utils._enums import ConfigTypeEnum


class LoggingRevision(Base, CreatedAtMixin, UpdatedAtMixin):
    __table_args__ = (
        Index(
            "ix_logging_revision_guild_config_created",
            "guild_id",
            "config_type",
            "created_at",
        ),
    )

    revision_id: Mapped[str] = mapped_column(primary_key=True, nullable=False)
    down_revision_id: Mapped[str] = mapped_column(String, nullable=True)

    config_type: Mapped[ConfigTypeEnum] = mapped_column(
        Enum(
            ConfigTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    old_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'[]'::json"),
    )
    new_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'[]'::json"),
    )
