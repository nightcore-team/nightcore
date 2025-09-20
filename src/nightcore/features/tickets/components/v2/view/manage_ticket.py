"""View for paginating infractions."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

import discord
from discord import ButtonStyle, CategoryChannel, Guild, Member, TextChannel
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models import GuildTicketsConfig
from src.infra.db.models._enums import ChannelType, TicketStateEnum
from src.infra.db.operations import (
    get_head_moderation_access_roles,
    get_latest_user_ticket,
    get_moderation_access_roles,
    get_specified_channel,
)
from src.nightcore.components.embed import ErrorEmbed, MissingPermissionsEmbed
from src.nightcore.features.tickets.utils import extract_id_from_str
from src.nightcore.utils import (
    discord_ts,
    ensure_member_exists,
    ensure_messageable_channel_exists,
    has_any_role_from_sequence,
)

logger = logging.getLogger(__name__)


class TicketStateViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        state: TicketStateEnum,
        moderator_id: int,
        author_id: int,
    ) -> None:
        super().__init__(timeout=None)

        # important: clear previous items to avoid duplicate custom_id
        self.clear_items()

        container = Container[Self]()

        message: str = ""
        match state:
            case TicketStateEnum.OPENED:
                message = "Ticket was opened by {}"
            case TicketStateEnum.PINNED:
                message = "Ticket was pinned by {}"
            case TicketStateEnum.CLOSED:
                message = "Ticket was closed by {}"
            case _:
                message = "Invalid state."

        container.add_item(TextDisplay[Self](f"### <@{author_id}>"))
        container.add_item(Separator[Self]())
        container.add_item(
            TextDisplay[Self](message.format(f"<@{moderator_id}>"))
        )
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )
        self.add_item(container)


class ManageTicketButtons(ActionRow["ManageTicketViewV2"]):
    def __init__(self):
        super().__init__()

    @button(
        style=ButtonStyle.grey,
        label="Pin",
        emoji="📌",
        custom_id="ticket:pin",
    )
    async def pin_ticket(
        self, interaction: Interaction, button: Button["ManageTicketViewV2"]
    ):
        """Pin the ticket."""
        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)
        user = cast(Member, interaction.user)

        if view.interaction_user_id is None:
            for component in interaction.message.components:  # type: ignore
                for child in component.children:  # type: ignore
                    if (
                        isinstance(child, discord.components.TextDisplay)
                        and child.id == 4
                    ):
                        view.interaction_user_id = extract_id_from_str(
                            child.content
                        )
                        logger.info(
                            "Extracted interaction_user_id %s from message in guild %s",  # noqa: E501
                            view.interaction_user_id,
                            guild.id,
                        )
                        break
        else:
            ...

        await interaction.response.defer()

        ticket_author = await ensure_member_exists(
            guild, cast(int, view.interaction_user_id)
        )
        if ticket_author is None:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Failed to pin ticket",
                    "Ticket author not found in this guild. You can close the ticket instead.",  # noqa: E501
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        async with view.bot.uow.start() as session:
            moderation_access_roles = await get_moderation_access_roles(
                session,
                guild_id=guild.id,
            )
            if not has_any_role_from_sequence(user, moderation_access_roles):
                return await interaction.followup.send(
                    embed=MissingPermissionsEmbed(
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            ticket = await get_latest_user_ticket(
                session,
                guild_id=guild.id,
                user_id=cast(int, view.interaction_user_id),
            )

            pinned_tickets_category_id = cast(
                int,
                await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildTicketsConfig,
                    channel_type=ChannelType.PINNED_TICKETS_CATEGORY,
                ),
            )

            if ticket is None:
                logger.warning(
                    "No ticket found for user %s in guild %s",
                    user.id,
                    guild.id,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Failed to pin ticket",
                        "No ticket found for this user.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            if ticket.state == TicketStateEnum.CLOSED:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Failed to pin ticket",
                        "You cannot pin a closed ticket.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            if ticket.state == TicketStateEnum.PINNED:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Failed to pin ticket",
                        "This ticket is already pinned by another moderator.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            ticket.moderator_id = user.id
            ticket.state = TicketStateEnum.PINNED

        pinned_tickets_category = await ensure_messageable_channel_exists(
            guild=guild,
            channel_id=pinned_tickets_category_id,
        )
        if pinned_tickets_category is None:
            logger.error(
                "Pinned tickets category %s not found in guild %s",
                pinned_tickets_category_id,
                guild.id,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Failed to pin ticket",
                    "Pinned tickets category is not configured correctly.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await channel.edit(
            category=cast(CategoryChannel, pinned_tickets_category),
            overwrites=channel.overwrites,
        )

        await interaction.followup.send(
            view=TicketStateViewV2(
                bot=view.bot,
                state=TicketStateEnum.PINNED,
                moderator_id=interaction.user.id,
                author_id=ticket.author_id,
            ),
        )

        logger.info(
            "Ticket %s pinned by user %s in guild %s",
            ticket.ticket_number,
            interaction.user.id,
            guild.id,
        )

    @button(
        style=ButtonStyle.grey,
        label="Reopen",
        emoji="📂",
        custom_id="ticket:reopen",
    )
    async def reopen_ticket(
        self, interaction: Interaction, button: Button["ManageTicketViewV2"]
    ):
        """Reopen the ticket."""
        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)
        user = cast(Member, interaction.user)

        # TODO: вынести в отдельную функцию, возможно
        if view.interaction_user_id is None:
            for component in interaction.message.components:  # type: ignore
                for child in component.children:  # type: ignore
                    if (
                        isinstance(child, discord.components.TextDisplay)
                        and child.id == 4
                    ):
                        view.interaction_user_id = extract_id_from_str(
                            child.content
                        )
                        logger.info(
                            "Extracted interaction_user_id %s from message in guild %s",  # noqa: E501
                            view.interaction_user_id,
                            guild.id,
                        )
                        break
        else:
            ...

        await interaction.response.defer()

        ticket_author = await ensure_member_exists(
            guild, cast(int, view.interaction_user_id)
        )
        if ticket_author is None:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Failed to reopen ticket",
                    "Ticket author not found in this guild.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        async with view.bot.uow.start() as session:
            moderation_access_roles = await get_head_moderation_access_roles(
                session,
                guild_id=guild.id,
            )
            if not has_any_role_from_sequence(user, moderation_access_roles):
                return await interaction.followup.send(
                    embed=MissingPermissionsEmbed(
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            ticket = await get_latest_user_ticket(
                session,
                guild_id=guild.id,
                user_id=cast(int, view.interaction_user_id),
            )

            pinned_tickets_category_id = cast(
                int,
                await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildTicketsConfig,
                    channel_type=ChannelType.PINNED_TICKETS_CATEGORY,
                ),
            )

            if ticket is None:
                logger.warning(
                    "No ticket found for user %s in guild %s",
                    user.id,
                    guild.id,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Failed to reopen ticket",
                        "No ticket found for this user.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            if ticket.state == TicketStateEnum.OPENED:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Failed to reopen ticket",
                        "You cannot reopen an opened ticket. Just pin it.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            if ticket.state == TicketStateEnum.PINNED:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Failed to reopen ticket",
                        "This ticket is already pinned by another moderator.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            ticket.moderator_id = user.id
            ticket.state = TicketStateEnum.PINNED

        pinned_tickets_category = await ensure_messageable_channel_exists(
            guild=guild,
            channel_id=pinned_tickets_category_id,
        )
        if pinned_tickets_category is None:
            logger.error(
                "Pinned tickets category %s not found in guild %s",
                pinned_tickets_category_id,
                guild.id,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Failed to reopen ticket",
                    "Pinned tickets category is not configured correctly.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        overwrites = channel.overwrites
        overwrites[ticket_author] = discord.PermissionOverwrite(
            read_messages=True,
            send_messages=True,
            attach_files=True,
            read_message_history=True,
        )

        await channel.edit(
            category=cast(CategoryChannel, pinned_tickets_category),
            overwrites=overwrites,
        )

        await interaction.followup.send(
            view=TicketStateViewV2(
                bot=view.bot,
                state=TicketStateEnum.OPENED,
                moderator_id=interaction.user.id,
                author_id=ticket.author_id,
            ),
        )

        logger.info(
            "Ticket %s reopened by user %s in guild %s",
            ticket.ticket_number,
            user.id,
            guild.id,
        )

    @button(
        style=ButtonStyle.grey,
        label="Close",
        emoji="🔒",
        custom_id="ticket:close",
    )
    async def close_ticket(
        self, interaction: Interaction, button: Button["ManageTicketViewV2"]
    ):
        """Close the ticket."""
        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)
        user = cast(Member, interaction.user)

        if view.interaction_user_id is None:
            for component in interaction.message.components:  # type: ignore
                for child in component.children:  # type: ignore
                    if (
                        isinstance(child, discord.components.TextDisplay)
                        and child.id == 4
                    ):
                        view.interaction_user_id = extract_id_from_str(
                            child.content
                        )
                        logger.info(
                            "Extracted interaction_user_id %s from message in guild %s",  # noqa: E501
                            view.interaction_user_id,
                            guild.id,
                        )
                        break
        else:
            ...

        await interaction.response.defer()

        ticket_author = await ensure_member_exists(
            guild, cast(int, view.interaction_user_id)
        )

        async with view.bot.uow.start() as session:
            moderation_access_roles = await get_moderation_access_roles(
                session,
                guild_id=guild.id,
            )
            if not has_any_role_from_sequence(user, moderation_access_roles):
                return await interaction.followup.send(
                    embed=MissingPermissionsEmbed(
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            ticket = await get_latest_user_ticket(
                session,
                guild_id=guild.id,
                user_id=cast(int, view.interaction_user_id),
            )

            closed_tickets_category_id = cast(
                int,
                await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildTicketsConfig,
                    channel_type=ChannelType.CLOSED_TICKETS_CATEGORY,
                ),
            )

            if ticket is None:
                logger.warning(
                    "No ticket found for user %s in guild %s",
                    user.id,
                    guild.id,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Failed to close ticket",
                        "No ticket found for this user.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            if ticket.state == TicketStateEnum.CLOSED:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Failed to close ticket",
                        "This ticket is already closed.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            ticket.moderator_id = user.id
            ticket.state = TicketStateEnum.CLOSED

        closed_tickets_category = await ensure_messageable_channel_exists(
            guild=guild,
            channel_id=closed_tickets_category_id,
        )
        if closed_tickets_category is None:
            logger.error(
                "Closed tickets category %s not found in guild %s",
                closed_tickets_category_id,
                guild.id,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Failed to close ticket",
                    "Pinned tickets category is not configured correctly.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        overwrites = channel.overwrites
        if ticket_author is not None:
            overwrites[ticket_author] = discord.PermissionOverwrite(
                read_messages=False,
                send_messages=False,
            )
        overwrites[guild.default_role] = discord.PermissionOverwrite(
            read_messages=False,
            send_messages=False,
        )

        await channel.edit(
            category=cast(CategoryChannel, closed_tickets_category),
            overwrites=overwrites,
        )

        await interaction.followup.send(
            view=TicketStateViewV2(
                bot=view.bot,
                state=TicketStateEnum.CLOSED,
                moderator_id=interaction.user.id,
                author_id=ticket.author_id,
            ),
        )

        logger.info(
            "Ticket %s closed by user %s in guild %s",
            ticket.ticket_number,
            user.id,
            guild.id,
        )


class ManageTicketViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        ping_role_id: int | None = None,
        interaction_user_id: int | None = None,
    ):
        """Create the layout view component."""
        super().__init__(timeout=None)
        self.bot = bot
        self.ping_role_id = cast(int, ping_role_id)
        self.interaction_user_id = interaction_user_id

        # important: clear previous items to avoid duplicate custom_id
        self.clear_items()

        container = Container[Self]()

        # Header
        container.add_item(TextDisplay[Self](f"### <@&{ping_role_id}>"))
        container.add_item(Separator[Self]())

        # main text
        container.add_item(
            TextDisplay[Self](
                f"### Dear <@{interaction_user_id}>, \nif you have any complaints regarding moderator service, please contact the [Arz Guard forum](https://forum.arzguard.com)."  # noqa: E501
            )
        )

        # action row
        container.add_item(Separator[Self]())
        container.add_item(ManageTicketButtons())
        container.add_item(Separator[Self]())

        # Footer
        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)


# TODO: add task for deleting old closed tickets after X days
# TODO: add event for logging tickets
# TODO: fix reopening tickets (moderator who reopened rewrite moderator_id in db)  # noqa: E501
