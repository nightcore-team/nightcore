"""
Order notification view v2 component.

Used for displaying notifications about shop order status changes.
"""

from typing import Self

from discord import Color
from discord.ui import (
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

from src.utils._enums import ShopOrderStateEnum


class CoinsShopOrderNotifyViewV2(LayoutView):
    """Shop notify view v2."""

    def __init__(
        self,
        state: ShopOrderStateEnum,
        moderator_id: int,
        user_balance_before: float,
        user_balance_after: float,
        item_name: str,
        item_cost: float,
        custom_id: int,
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(
            TextDisplay[Self](
                "### <:nightcorepShopping:1540451786853191790> Уведомление о покупке товара\n"  # noqa: E501
            )
        )

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

        container.add_item(
            TextDisplay[Self](
                "### <:nightcoreInfo:1540439225877528626> Информация о покупке:"  # noqa: E501
            )
        )

        container.add_item(
            TextDisplay[Self](
                f"> Баланс пользователя (до): **{user_balance_before}**\n"
                f"> Баланс пользователя (после): **{user_balance_after}**\n"
                f"> Товар: **{item_name}**\n"
                f"> Цена: **{item_cost}**\n"
                f"> Идентификатор покупки: **{custom_id}**"
            )
        )
        container.add_item(Separator[Self]())

        self.add_item(container)
