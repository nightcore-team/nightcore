"""TicketState model for the Nightcore bot database."""

from uuid import UUID as UUIDBuiltIn  # noqa: N811
from uuid import uuid4

from sqlalchemy import BigInteger, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._enums import ShopOrderStateEnum
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class ShopOrderState(IdIntegerMixin, Base):
    custom_id: Mapped[UUIDBuiltIn] = mapped_column(
        UUID(as_uuid=True),
        default=uuid4(),
        nullable=False,
        unique=True,
    )
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    state: Mapped[ShopOrderStateEnum] = mapped_column(
        Enum(
            ShopOrderStateEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )
