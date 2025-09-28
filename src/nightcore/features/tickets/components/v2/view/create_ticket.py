"""View for paginating infractions."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

import discord
from discord import ButtonStyle, CategoryChannel, Guild, Member
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

from src.infra.db.models import (
    GuildLoggingConfig,
    GuildTicketsConfig,
    TicketState,
)
from src.infra.db.models._enums import ChannelType, TicketStateEnum
from src.infra.db.operations import (
    get_latest_user_ticket,
    get_or_create_user,
    get_specified_channel,
    get_specified_guild_config,
)
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.tickets.events.dto import TicketEventData
from src.nightcore.utils import discord_ts, ensure_messageable_channel_exists

from .manage_ticket import ManageTicketViewV2

logger = logging.getLogger(__name__)


# TODO: add missing permissions and error embeds
class CreateTicketButton(ActionRow["CreateTicketViewV2"]):
    def __init__(self):
        super().__init__()

    @button(
        style=ButtonStyle.grey,
        label="Create Ticket",
        emoji="<:29909ticket:1418324338142220309>",
        custom_id="ticket:create",
    )
    async def create_ticket(
        self, interaction: Interaction, button: Button["CreateTicketViewV2"]
    ):
        """Button to create a ticket."""
        view = cast("CreateTicketViewV2", self.view)
        guild = cast(Guild, interaction.guild)
        user = cast(Member, interaction.user)

        await interaction.response.defer(thinking=True, ephemeral=True)

        if not guild.me.guild_permissions.manage_channels:
            return await interaction.followup.send(
                "I do not have permission to manage channels.",
            )

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
                return await interaction.followup.send(
                    "Ticket system is not configured in this server.",
                )

            if not all(
                [
                    guild_config.create_ticket_ping_role_id,
                    guild_config.new_tickets_category_id,
                    guild_config.pinned_tickets_category_id,
                    guild_config.closed_tickets_category_id,
                ]
            ):
                logger.error(
                    "Not all ticket categories are configured in guild %s",
                    guild.id,
                )
                return await interaction.followup.send(
                    "Ticket system is not configured in this server.",
                )

            dbuser, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=user.id
            )
            if dbuser.ticket_ban:
                return await interaction.followup.send(
                    "You are ticket banned and cannot create tickets.",
                )

            last_ticket = await get_latest_user_ticket(
                session, guild_id=guild.id, user_id=user.id
            )
            if last_ticket and last_ticket.state != TicketStateEnum.CLOSED:
                return await interaction.followup.send(
                    "You already have an open ticket.",
                )
            else:
                current_tickets_count = guild_config.tickets_count + 1

                first_ticket = TicketState(
                    ticket_number=current_tickets_count,
                    guild_id=guild.id,
                    author_id=user.id,
                    state=TicketStateEnum.OPENED,
                )

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
                return await interaction.followup.send(
                    "Ticket system is not configured in this server.",
                )

            try:
                overwrites = new_tickets_category.overwrites
                overwrites[user] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    attach_files=True,
                    read_message_history=True,
                )

                channel = await guild.create_text_channel(
                    name=f"ticket-{current_tickets_count}",
                    category=new_tickets_category,
                    overwrites=overwrites,
                )

                first_ticket.channel_id = channel.id
                session.add(first_ticket)

                message = await channel.send(
                    view=ManageTicketViewV2(
                        view.bot,
                        ping_role_id=guild_config.create_ticket_ping_role_id,
                        interaction_user_id=interaction.user.id,
                    ),
                )

                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_TICKETS,
                )

                if logging_channel_id:
                    view.bot.dispatch(
                        "ticket_changed",
                        data=TicketEventData(
                            guild,
                            channel.id,
                            user.id,
                            None,
                            TicketStateEnum.OPENED,
                            logging_channel_id,
                        ),
                    )

                await interaction.followup.send(
                    f"Your ticket has been created: {message.jump_url}",
                )
            except Exception as e:
                logger.error(
                    "Failed to create ticket channel in guild %s, category: %s, %s",  # noqa: E501
                    guild.id,
                    new_tickets_category.id,
                    e,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ticket Creation Failed",
                        "Failed to create ticket channel.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
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
