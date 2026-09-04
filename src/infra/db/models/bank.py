"""Bank model for the Nightcore bot database."""

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._mixins import (
    CreatedAtMixin,
    IdIntegerMixin,
    UpdatedAtMixin,
)
from src.infra.db.models.base import Base

if TYPE_CHECKING:
    from src.infra.db.models.user import User


class BankAccount(IdIntegerMixin, CreatedAtMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "guild_id",
            "user_id",
            name="ux_user_guild_bank_account",
        ),
    )

    guild_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        back_populates="bank_account",
        uselist=False,
        cascade="all, delete-orphan",
    )

    deposit: Mapped["Deposit | None"] = relationship(
        back_populates="bank_account",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    extra_wallets: Mapped[list["ExtraWallet"]] = relationship(
        back_populates="bank_account",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Deposit(IdIntegerMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("bankaccount.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    coins: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    bank_account: Mapped["BankAccount"] = relationship(
        back_populates="deposit",
    )


class ExtraWallet(IdIntegerMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    bank_account_id: Mapped[int] = mapped_column(
        ForeignKey("bankaccount.id", ondelete="CASCADE"),
        nullable=False,
    )

    coins: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    slot: Mapped[int] = mapped_column(nullable=False)

    bank_account: Mapped["BankAccount"] = relationship(
        back_populates="extra_wallets",
    )
