"""V2 activate view for user's VIP-statuses.

Displays the user's own VIP-statuses with their bonuses and an
"activate" button per status. Already-activated statuses have their
button disabled.
"""

from typing import TYPE_CHECKING, Any, Self

from discord import ButtonStyle, Color
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

from src.infra.db.models._annot import UserVipStatusAnnot

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class VipStatusActivateViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        content: list[TextDisplay[Any]],
        statuses: list[UserVipStatusAnnot],
    ):
        super().__init__(timeout=None)

        self.content = content
        self.statuses = statuses
        self.bot = bot

        self.make_component()

    def make_component(self) -> Self:
        """Create a new component for the current page."""

        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(
            TextDisplay(
                "### <:nightcoreGem:1540406663377453097> Активация VIP-статусов"  # noqa: E501
            )
        )
        container.add_item(Separator())
        container.add_item(
            TextDisplay(
                "**Ваши VIP-статусы.**\n"
                "> Нажмите на кнопку, чтобы активировать VIP-статус"
            )
        )
        container.add_item(Separator())

        for item in self.content:
            container.add_item(item)

        container.add_item(Separator[Self]())

        activate_row = ActionRow[Self]()
        for status in self.statuses:
            label = f"Активировать {status['name']}"[:79]

            activate_row.add_item(
                Button(
                    label=label,
                    style=ButtonStyle.secondary,
                    emoji=status["emoji_str"],
                    custom_id=f"vip:activate:{status['vip_id']}",
                    disabled=status["is_active"],
                )
            )

        container.add_item(activate_row)

        container.add_item(Separator())

        self.add_item(container)

        return self
