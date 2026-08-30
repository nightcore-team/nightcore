"""Coins shop order view v2."""

from typing import Self

from discord import ButtonStyle, Color
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)


class CoinsShopOrderViewV2(LayoutView):
    """Coins shop order view v2."""

    def __init__(
        self,
        ping_roles_ids: list[int] | None = None,
        user_id: int | None = None,
        user_balance_before: float | None = None,
        user_balance_after: float | None = None,
        item_name: str | None = None,
        item_price: float | None = None,
        disable_buttons: bool = False,
    ) -> None:
        super().__init__(timeout=None)

        """Create the coins shop order view component."""
        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        if ping_roles_ids:
            container.add_item(
                TextDisplay[Self](
                    f"{','.join(f'<@&{rid}>' for rid in ping_roles_ids)}"
                )
            )
            container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                "## <:nightcorepShopping:1540451786853191790> Запрос на покупку товара"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self]("### Информация о покупке:"))

        container.add_item(
            TextDisplay[Self](
                f"> Пользователь: <@{user_id}> (`{user_id}`)\n"
                f"> Баланс пользователя (до): **{user_balance_before}**\n"
                f"> Баланс пользователя (после): **{user_balance_after}**\n"
                f"> Товар: **{item_name}**\n"
                f"> Цена: **{item_price}**"
            )
        )

        container.add_item(Separator[Self]())

        container.add_item(
            ActionRow[Self](
                Button(
                    label="Одобрить",
                    style=ButtonStyle.grey,
                    emoji="<:nightcoreAccept:1540450035907436625>",
                    custom_id="coins_shop:approve",
                    disabled=disable_buttons,
                ),
                Button(
                    label="Отклонить",
                    style=ButtonStyle.grey,
                    emoji="<:nightcoreDecline:1540450233417338960>",
                    custom_id="coins_shop:decline",
                    disabled=disable_buttons,
                ),
            )
        )

        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                "Товар будет выдан после проверки модерацией вашего запроса."
            )
        )

        self.add_item(container)
