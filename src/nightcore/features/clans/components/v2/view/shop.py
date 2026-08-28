"""Clan shop view."""

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

from src.utils._enums import ShopOrderStateEnum


class ClanShopViewV2(LayoutView):
    """Clan shop view v2."""

    def __init__(
        self,
        ping_roles_ids: list[int] | None = None,
        user_id: int | None = None,
        clan_name: str | None = None,
        clan_balance_before: float | None = None,
        clan_balance_after: float | None = None,
        item_name: str | None = None,
        item_cost: float | None = None,
        disable_buttons: bool = False,
    ) -> None:
        super().__init__(timeout=None)

        """Create the clan shop view component."""
        container = Container[Self](accent_color=Color.from_str("#9B7EDE"))

        if ping_roles_ids:
            container.add_item(
                TextDisplay[Self](
                    f"{','.join(f'<@&{rid}>' for rid in ping_roles_ids)}"
                )
            )

        container.add_item(Separator[Self]())
        container.add_item(
            TextDisplay[Self](
                "## <:nightcoreShoppingPurple:1540718246523568268> Запрос на покупку товара"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self]("### Информация о покупке:"))

        container.add_item(
            TextDisplay[Self](
                f"> Пользователь: <@{user_id}> (`{user_id}`)\n"
                f"> Клан: **{clan_name}**\n"
                f"> Баланс клана (до): **{clan_balance_before}**\n"
                f"> Баланс клана (после): **{clan_balance_after}**\n"
                f"> Товар: **{item_name}**\n"
                f"> Цена: **{item_cost}**"
            )
        )

        container.add_item(Separator[Self]())

        container.add_item(
            ActionRow[Self](
                Button(
                    label="Одобрить",
                    style=ButtonStyle.grey,
                    emoji="<:nightcoreAcceptPurple:1540717637745508402>",
                    custom_id="clan_shop:approve",
                    disabled=disable_buttons,
                ),
                Button(
                    label="Отклонить",
                    style=ButtonStyle.grey,
                    emoji="<:nightcoreDeclinePurple:1540717713318477824>",
                    custom_id="clan_shop:decline",
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


class ShopNotifyViewV2(LayoutView):
    """Shop notify view v2."""

    def __init__(
        self,
        state: ShopOrderStateEnum,
        moderator_id: int,
        clan_name: str,
        clan_balance_before: float,
        clan_balance_after: float,
        item_name: str,
        item_cost: float,
        custom_id: int,
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#9B7EDE"))

        container.add_item(
            TextDisplay[Self](
                "## <:9183shoppingcart:1442921975851778310> Уведомление о покупке товара"  # noqa: E501
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
                f"> Клан: **{clan_name}**\n"
                f"> Баланс клана (до): **{clan_balance_before}**\n"
                f"> Баланс клана (после): **{clan_balance_after}**\n"
                f"> Товар: **{item_name}**\n"
                f"> Цена: **{item_cost}**\n"
                f"> Идентификатор покупки: **{custom_id}**"
            )
        )

        self.add_item(container)
