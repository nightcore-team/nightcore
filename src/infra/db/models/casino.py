"""Casino model for the Nightcore bot database."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infra.db.models._enums import (
    CasinoGameStateEnum,
    CasinoGameTypeEnum,
    CasinoPlayersTypeEnum,
)
from src.infra.db.models._mixins import IdIntegerMixin
from src.infra.db.models.base import Base


class CasinoGame(IdIntegerMixin, Base):
    # discord guild id
    guild_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    # discord user id who initiated the game
    initiator_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # discord message id with game component
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    # type of the casino game
    game_type: Mapped[CasinoGameTypeEnum] = mapped_column(
        Enum(
            CasinoGameTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
    )
    # type of players in the game
    players_type: Mapped[CasinoPlayersTypeEnum] = mapped_column(
        Enum(
            CasinoPlayersTypeEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        nullable=False,
        default=CasinoPlayersTypeEnum.SINGLE,
    )
    # current state of the game
    state: Mapped[CasinoGameStateEnum] = mapped_column(
        Enum(
            CasinoGameStateEnum,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],  # type: ignore
            validate_strings=True,
        ),
        default=CasinoGameStateEnum.PENDING,
    )
    # end time of the game
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    # relathionship to bets
    bets: Mapped[list["CasinoBet"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class CasinoBet(IdIntegerMixin, Base):
    # discord user id who placed the bet
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # amount of coins bet
    amount: Mapped[int] = mapped_column(nullable=False)
    # chosen color for the bet
    color: Mapped[str] = mapped_column(nullable=False)
    # foreign key to the casino game
    game_id: Mapped[int] = mapped_column(
        ForeignKey("casino_game.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # relationship to the casino game
    game: Mapped["CasinoGame"] = relationship(back_populates="bets")
