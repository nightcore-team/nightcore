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
