"""View for paginating infractions."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import ButtonStyle
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    Item,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class CreateTicketButton(ActionRow["CreateTicketViewV2"]):
    def __init__(self):
        super().__init__()

    async def interaction_check(
        self,
        interaction: Interaction,
    ) -> bool:
        """Ensure that only the author can interact with the view."""
        await interaction.response.send_message(
            "You can't manage this pagination.", ephemeral=True
        )
        return False

    @button(
        style=ButtonStyle.grey,
        label="Create Ticket",
        emoji="<:3936faqbadge:1417212058902204539>",
        custom_id="ticket:create",
    )
    async def create_ticket(
        self, interaction: Interaction, button: Button["CreateTicketViewV2"]
    ):
        """Go to the previous page."""
        ...


class CreateTicketViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
    ):
        """Create the layout view component."""
        super().__init__(timeout=None)
        self.bot = bot

        # important: clear previous items to avoid duplicate custom_id
        self.clear_items()

        container = Container[Self]()

        # Header
        container.add_item(TextDisplay[Self]("## Ask your question"))
        container.add_item(Separator[Self]())

        # main text
        container.add_item(
            TextDisplay[Self](
                "Here you can ask support agents a question regarding...\n...the rules or behavior on the Discord server"  # noqa: E501
            )
        )

        # action row
        container.add_item(Separator[Self]())
        container.add_item(CreateTicketButton())
        container.add_item(Separator[Self]())

        # Footer
        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
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
