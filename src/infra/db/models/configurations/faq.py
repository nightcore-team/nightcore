"""Guild FAQ configuration model."""

from typing import Any

from sqlalchemy import JSON, BigInteger, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._annot import FAQPageAnnot
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class GuildFaqConfig(IdIntegerMixin, Base):
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
    )

    faq: Mapped[list[FAQPageAnnot]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )

    __version__ = 1

    @staticmethod
    def patch_revision(data: dict[str, Any]) -> dict[str, Any]:
        """Apply a patch to a config revision data dict."""
        ...
