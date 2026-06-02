from sqlalchemy import BigInteger, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildForumConfig(IdIntegerMixin, Base):
    """Forum configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    section_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, unique=True
    )
    channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, unique=True
    )
    role_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, unique=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    @property
    def available(self) -> bool:  # noqa: D102
        return self.section_id is not None
