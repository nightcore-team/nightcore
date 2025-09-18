"""View for paginating infractions."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, CategoryChannel, Guild
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

from src.infra.db.models import GuildTicketsConfig, TicketState
from src.infra.db.models._enums import TicketStateEnum
from src.infra.db.operations import (
    get_latest_user_ticket,
    get_or_create_user,
    get_specified_guild_config,
)
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.utils import discord_ts, ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


class CreateTicketButton(ActionRow["CreateTicketViewV2"]):
    def __init__(self):
        super().__init__()

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
        view = cast("CreateTicketViewV2", self.view)
        guild = cast(Guild, interaction.guild)

        logger.info("-------------------------------------------------")

        async with view.bot.uow.start() as session:
            guild_config = await get_specified_guild_config(
                session,
                config_type=GuildTicketsConfig,
                guild_id=guild.id,
            )
            if guild_config is None:
                logger.error(
                    "Failed to find ticket guild config in guild %s",
                    guild.id,
                )
                return await interaction.response.send_message(
                    "Ticket system is not configured in this server.",
                    ephemeral=True,
                )

            if not all(
                [
                    guild_config.new_tickets_category_id,
                    guild_config.pinned_tickets_category_id,
                    guild_config.closed_tickets_category_id,
                ]
            ):
                logger.error(
                    "Not all ticket categories are configured in guild %s",
                    guild.id,
                )
                return await interaction.response.send_message(
                    "Ticket system is not configured in this server.",
                    ephemeral=True,
                )

            user, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=interaction.user.id
            )
            if user.ticket_ban:
                return await interaction.response.send_message(
                    "You are ticket banned and cannot create tickets.",
                    ephemeral=True,
                )

            last_ticket = await get_latest_user_ticket(
                session, guild_id=guild.id, user_id=interaction.user.id
            )
            if last_ticket and last_ticket.state != TicketStateEnum.CLOSED:
                return await interaction.response.send_message(
                    "You already have an open ticket.",
                    ephemeral=True,
                )

            current_tickets_count = guild_config.tickets_count + 1

            if not last_ticket:
                first_ticket = TicketState(
                    ticket_number=current_tickets_count,
                    guild_id=guild.id,
                    author_id=interaction.user.id,
                    moderator_id=interaction.user.id,
                    state=TicketStateEnum.OPEN,
                )
                session.add(first_ticket)

                guild_config.tickets_count = current_tickets_count

            new_tickets_category = cast(
                CategoryChannel,
                await ensure_messageable_channel_exists(
                    guild,
                    guild_config.new_tickets_category_id,  # type: ignore
                ),
            )
            if not new_tickets_category:
                logger.error(
                    "Failed to find new tickets category in guild %s",
                    guild.id,
                )
                return await interaction.response.send_message(
                    "Ticket system is not configured in this server.",
                    ephemeral=True,
                )

            try:
                channel = await guild.create_text_channel(
                    name=f"ticket-{current_tickets_count}",
                    category=new_tickets_category,
                    overwrites=new_tickets_category.overwrites,
                )
                message = await channel.send(
                    f"{interaction.user.mention}, thank you for creating a ticket."  # noqa: E501
                )
                await interaction.response.send_message(
                    f"Your ticket has been created: {message.jump_url}",
                    ephemeral=True,
                )
                logger.info(
                    "-------------------------------------------------"
                )
            except Exception as e:
                logger.error(
                    "Failed to create ticket channel in guild %s, category: %s, %s",  # noqa: E501
                    guild.id,
                    new_tickets_category.id,
                    e,
                )
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ticket Creation Failed",
                        "Failed to create ticket channel.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )


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
