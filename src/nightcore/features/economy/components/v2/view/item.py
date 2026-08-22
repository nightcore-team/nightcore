"""
Award notification view v2 component.

Used for displaying a notification when an item is awarded to a user.
"""

from typing import TYPE_CHECKING, Self

from discord import Color
from discord.ui import Container, LayoutView, Separator, TextDisplay

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class AwardNotificationViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_id: int,
        item_name: str,
        amount: int,
        reason: str | None = None,
    ):
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(
            TextDisplay[Self](
                "### <:nightcoreStarUp:1540441938979983482> Уведомление о выдаче предмета\n"  # noqa: E501
            )
        )
        container.add_item(
            TextDisplay[Self](
                f"<@{user_id}> вам выдал(а) предмет.\n> Причина: {reason or 'Не указана'}"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(TextDisplay[Self]("### Информация о предмете: "))
        container.add_item(
            TextDisplay[Self](
                f"> Название: **{item_name}**\n> Количество: **{amount}**"
            )
        )

        self.add_item(container)
