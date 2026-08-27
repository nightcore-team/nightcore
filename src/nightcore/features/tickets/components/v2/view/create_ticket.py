"""View for creating tickets."""

from typing import Self

from discord import ButtonStyle, Color
from discord.ui import (
    ActionRow,
    Button,
    Container,
    Item,
    LayoutView,
    Separator,
    TextDisplay,
)


class CreateTicketViewV2(LayoutView):
    def __init__(self):
        """Create the layout view component."""
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#5DADE2"))

        # Header
        container.add_item(TextDisplay[Self]("## Задайте ваш вопрос"))
        container.add_item(Separator[Self]())

        # main text
        container.add_item(
            TextDisplay[Self](
                "Здесь вы можете задать вопрос агентам поддержки относительно...\n...правил или поведения на Discord сервере"  # noqa: E501
            )
        )

        # action row
        container.add_item(Separator[Self]())
        container.add_item(
            ActionRow(
                Button[Self](
                    style=ButtonStyle.grey,
                    label="Создать тикет",
                    emoji="<:nightcoreTicketNew:1540818406977052812>",
                    custom_id="ticket:create",
                )
            )
        )

        self.add_item(container)

    async def on_timeout(self):
        """Disable all buttons when the view times out."""

        def walk(item: Item[Self]):  # type: ignore
            if hasattr(item, "children"):
                for c in item.children:  # type: ignore
                    yield from walk(c)  # type: ignore
            yield item

        for comp in walk(self):  # type: ignore
            if isinstance(comp, Button):
                comp.disabled = True
