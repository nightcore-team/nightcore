"""Vip model for the Nightcore bot database."""

from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class VipStatus(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint("guild_id", "name", name="uv_guild_name_vip"),
        UniqueConstraint("guild_id", "role_id", name="ux_guild_role_vip"),
    )

    name: Mapped[str] = mapped_column(nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    deposit_max_balance: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default=text("0")
    )  # Max amount a user can hold in their deposit account
    deposit_interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0.0000,
        server_default=text("0.0000"),
    )  # Annual interest rate for deposits that overrides config value (e.g. 0.0100 = 1%)  # noqa: E501
    deposit_interest_cap_amount: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default=text("0")
    )  # Max interest a user can earn per payout cycle
    shop_discount: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=0.0000,
        server_default=text("0.0000"),
    )  # Economy shop discount
