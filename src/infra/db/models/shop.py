"""TicketState model for the Nightcore bot database."""

from sqlalchemy import JSON, BigInteger, Enum, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._annot import (
    ClanShopOrderPayloadAnnot,
    CoinsShopOrderPayloadAnnot,
)
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.utils._enums import ShopOrderStateEnum, ShopOrderTypeEnum


class ShopOrderState(IdIntegerMixin, Base):
    custom_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True
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

    type: Mapped[ShopOrderTypeEnum] = mapped_column(
        Enum(
            ShopOrderTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )

    payload: Mapped[ClanShopOrderPayloadAnnot | CoinsShopOrderPayloadAnnot] = (
        mapped_column(
            JSON,
            nullable=False,
            default=dict,
            server_default=text("'{}'::json"),
        )
    )
