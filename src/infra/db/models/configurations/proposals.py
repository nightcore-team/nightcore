"""Guild proposals configuration model."""

from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildProposalsConfig(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )
    create_proposal_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    proposals_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    __table_args__ = (
        CheckConstraint(
            "proposals_count >= 0", name="ck_proposals_count_nonnegative"
        ),
    )

    __version__ = 1

    @staticmethod
    def patch_revision(data: dict[str, Any]) -> dict[str, Any]:
        """Apply a patch to a config revision data dict."""
        ...
