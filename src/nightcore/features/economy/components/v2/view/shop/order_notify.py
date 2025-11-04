"""
Order notification view v2 component.

Used for displaying notifications about shop order status changes.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord.ui import (
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

from src.infra.db.models._enums import ShopOrderStateEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class CoinsShopOrderNotifyViewV2(LayoutView):
    """Shop notify view v2."""

    def __init__(
        self,
        bot: "Nightcore",
        state: ShopOrderStateEnum,
        moderator_id: int,
        user_balance_before: float,
        user_balance_after: float,
        item_name: str,
        item_price: float,
        custom_id: int,
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot

        container = Container[Self]()

        container.add_item(
            TextDisplay[Self](
                "## <:9183shoppingcart:1431625159235731516> Уведомление о покупке товара"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        description = ""
        if state == ShopOrderStateEnum.APPROVED:
            description = (
                f"<@{moderator_id}> одобрил(а) вашу покупку в магазине."
            )
        elif state == ShopOrderStateEnum.DENIED:
            description = (
                f"<@{moderator_id}> отклонил(а) вашу покупку в магазине."
            )

        container.add_item(TextDisplay[Self](f"{description}"))
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self]("### Информация о покупке:"))

        container.add_item(
            TextDisplay[Self](
                f"> Баланс пользователя (до): **{user_balance_before}**\n"
                f"> Баланс пользователя (после): **{user_balance_after}**\n"
                f"> Товар: **{item_name}**\n"
                f"> Цена: **{item_price}**\n"
                f"> Идентификатор покупки: **{custom_id}**"
            )
        )
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
