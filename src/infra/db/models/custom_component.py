"""Custom component model for the Nightcore bot database."""

from sqlalchemy import BigInteger, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._enums import ComponentTypeEnum
from src.infra.db.models._mixins import CreatedAtMixin, IdIntegerMixin
from src.infra.db.models.base import Base


class CustomComponent(IdIntegerMixin, CreatedAtMixin, Base):
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    moderator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[ComponentTypeEnum] = mapped_column(
        Enum(
            ComponentTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    author_text: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index(
            "ix_changestats_guild_id_name",
            "guild_id",
            "name",
        ),
    )
