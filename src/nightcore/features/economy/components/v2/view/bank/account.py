"""
Bank profile view v2 component.

Used for displaying information about user's bank profile.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import Container, LayoutView, Separator, TextDisplay

from src.nightcore.utils.time_utils import discord_ts

if TYPE_CHECKING:
    from src.infra.db.models._annot import ExtraWalletAnnot

EMOJIS = {
    1: "<:nightcoreOne:1545127499166523432>",
    2: "<:nightcoreTwo:1545127497258111017>",
    3: "<:nightcoreThree:1545127495316279426>",
}


class BankAccountViewV2(LayoutView):
    def __init__(
        self,
        user_id: int,
        coin_name: str,
        deposit_balance: int,
        deposit_interest_cap_amount: int,
        deposit_current_rate: float,
        deposit_last_updated_at: datetime,
        extra_wallets: list["ExtraWalletAnnot"],
    ):
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(
            TextDisplay[Self](
                "### <:nightcoreBank:1545104845139218472> Банковский аккаунт\n"
                f"> Пользователь: <@{user_id}>"
            )
        )
        container.add_item(Separator())
        container.add_item(
            TextDisplay[Self](
                "### <:nightcoreInfo:1540439225877528626>Состояние депозита\n"
                f"> <:nightcoreLevelUp:1540402294275969024> Баланс: {deposit_balance} {coin_name}\n"  # noqa: E501
                f"> <:nightcorePercent:1545112163742519349> Процентная ставка: {deposit_current_rate}, лимит для начисления процентов: {deposit_interest_cap_amount}\n"  # noqa: E501
                f"> Последнее начисление: {discord_ts(deposit_last_updated_at)}"  # noqa: E501
            )
        )

        if extra_wallets:
            container.add_item(Separator())

            add_separator = len(extra_wallets) > 1

            for idx, wallet in enumerate(extra_wallets, start=1):
                container.add_item(
                    TextDisplay[Self](
                        f"### <:nightcoreAccept:1540450035907436625> Extra-счёт <:nightcoreHash:1545371151885271040>{EMOJIS.get(wallet['slot'], idx)}\n"  # noqa: E501
                        f"> Последнее пополнение/снятие: {discord_ts(wallet['updated_at'])}"  # noqa: E501
                    )
                )
                if add_separator:
                    container.add_item(Separator())

        self.add_item(container)
