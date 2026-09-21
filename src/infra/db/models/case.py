"""Case model for the Nightcore bot database."""

import random
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._annot import CaseDropAnnot
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base
from src.utils._enums import CaseOpenSessionStatus


class Case(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint("guild_id", "name", name="ux_name_guild_case"),
    )

    name: Mapped[str] = mapped_column(nullable=False)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    drop: Mapped[list[CaseDropAnnot]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'::json"),
    )

    def open(self, amount: int = 1) -> list[CaseDropAnnot | None]:
        """Open case and get reward."""

        if not self.drop:
            return [None] * amount

        chances = [drop["chance"] for drop in self.drop]

        selected_indices = random.choices(
            range(len(self.drop)), weights=chances, k=amount
        )

        drops = [self.drop[i] for i in selected_indices]
        for drop in drops:
            drop["is_color_compensation"] = None

        return drops  # type: ignore


class CaseOpenSession(IdIntegerMixin, Base):
    __table_args__ = (
        ForeignKeyConstraint(
            ["guild_id", "user_id"],
            ["user.guild_id", "user.user_id"],
            ondelete="CASCADE",
        ),
        Index(
            "ix_caseopensession_status_expires_at",
            "status",
            "expires_at",
        ),
    )

    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("case.id", ondelete="CASCADE"),
        nullable=False,
    )
    rerolls_used: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[CaseOpenSessionStatus] = mapped_column(
        Enum(
            CaseOpenSessionStatus,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
        default=CaseOpenSessionStatus.PENDING,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    case: Mapped["Case"] = relationship()
    rewards: Mapped[list["CaseOpenReward"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="CaseOpenReward.position",
    )


class CaseOpenReward(IdIntegerMixin, Base):
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "position",
            name="uq_case_open_reward_position",
        ),
        Index("ix_caseopenreward_session_id", "session_id"),
    )

    session_id: Mapped[int] = mapped_column(
        ForeignKey("caseopensession.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(nullable=False)
    reward: Mapped[CaseDropAnnot] = mapped_column(JSON, nullable=False)
    reroll_count: Mapped[int] = mapped_column(nullable=False, default=0)

    session: Mapped[CaseOpenSession] = relationship(back_populates="rewards")
