from sqlalchemy import ARRAY, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildInfomakerConfig(IdIntegerMixin, Base):
    """Infomaker configuration for a guild."""

    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    admins_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    leaders_roles_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), nullable=True
    )
    admins_roles_logging_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    leaders_roles_logging_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
