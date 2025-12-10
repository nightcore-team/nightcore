"""View for managing tickets."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

import discord
from discord import (
    ButtonStyle,
    CategoryChannel,
    Color,
    Guild,
    Member,
    TextChannel,
)
from discord import app_commands
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

from src.infra.db.models import GuildLoggingConfig, GuildTicketsConfig
from src.infra.db.models._enums import ChannelType, TicketStateEnum
from src.infra.db.operations import (
    get_latest_user_ticket,
    get_specified_channel,
)
from src.nightcore.components.embed import ErrorEmbed, MissingPermissionsEmbed
from src.nightcore.features.tickets.events.dto import TicketEventData
from src.nightcore.utils import (
    discord_ts,
    ensure_member_exists,
    ensure_messageable_channel_exists,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
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

        self.clear_items()

        container = Container[Self]()

        message: str = ""
        match state:
            case TicketStateEnum.OPENED:
                message = "### Тикет был открыт модератором {}"
            case TicketStateEnum.PINNED:
                message = "### Тикет был закреплен модератором {}"
            case TicketStateEnum.CLOSED:
                message = "### Тикет был закрыт модератором {}"
            case _:
                message = "Неизвестное состояние."

        container.add_item(
            TextDisplay[Self](message.format(f"<@{moderator_id}>"))
        )
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)} | <@{author_id}>"  # type: ignore  # noqa: E501
            )
        )
        self.add_item(container)


class ManageTicketButtons(ActionRow["ManageTicketViewV2"]):
    def __init__(self):
        super().__init__()

    @button(
        style=ButtonStyle.grey,
        label="Закрепить",
        emoji="<:paperclip1:1442914563321368737>",
        custom_id="ticket:pin",
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def pin_ticket(
        self, interaction: Interaction, button: Button["ManageTicketViewV2"]
    ):
        """Pin the ticket."""

        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)
        user = cast(Member, interaction.user)

        await interaction.response.defer()

        if not guild.me.guild_permissions.manage_channels:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    "У меня нет прав на управление каналами.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        ticket_author_id = 0
        pinned_tickets_category_id = 0
        logging_channel_id: int | None = None

        async with view.bot.uow.start() as session:
            ticket_state = await get_latest_user_ticket(
                session, guild_id=guild.id, channel_id=channel.id
            )

            if ticket_state is None:
                outcome = "ticket_not_found"
            elif ticket_state.state == TicketStateEnum.CLOSED:
                outcome = "ticket_closed"
            elif ticket_state.state == TicketStateEnum.PINNED:
                outcome = "already_pinned"
            else:
                # Save ticket data
                ticket_author_id = ticket_state.author_id
                # Update ticket state to PINNED
                ticket_state.moderator_id = user.id
                ticket_state.state = TicketStateEnum.PINNED

                # Get pinned tickets category ID
                pinned_tickets_category_id = cast(
                    int,
                    await get_specified_channel(
                        session,
                        guild_id=guild.id,
                        config_type=GuildTicketsConfig,
                        channel_type=ChannelType.PINNED_TICKETS_CATEGORY,
                    ),
                )

                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_TICKETS,
                )

                outcome = "success"

        if outcome == "ticket_not_found":
            logger.warning(
                "No ticket found for user %s in guild %s",
                view.interaction_user_id,
                guild.id,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось закрепить тикет",
                    "Тикет не найден для этого пользователя.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "ticket_closed":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось закрепить тикет",
                    "Вы не можете закрепить закрытый тикет.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "already_pinned":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось закрепить тикет",
                    "Этот тикет уже закреплен другим модератором.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
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
                        "Не удалось закрепить тикет",
                        "Категория закрепленных тикетов не найдена.",
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
                    author_id=ticket_author_id,
                ),
            )

            # Dispatch event
            if logging_channel_id:
                view.bot.dispatch(
                    "ticket_changed",
                    data=TicketEventData(
                        guild,
                        channel.id,
                        ticket_author_id,
                        interaction.user.id,
                        TicketStateEnum.PINNED,
                        logging_channel_id,
                    ),
                )

            logger.info(
                "Ticket pinned by user %s in guild %s",
                interaction.user.id,
                guild.id,
            )

    @button(
        style=ButtonStyle.grey,
        label="Открыть",
        emoji="<:unlock:1442914794377187448>",
        custom_id="ticket:reopen",
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.HEAD_MODERATION_ACCESS)  # type: ignore
    async def reopen_ticket(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["ManageTicketViewV2"],
    ):
        """Reopen the ticket."""

        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)

        await interaction.response.defer()

        if not guild.me.guild_permissions.manage_channels:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    "У меня нет прав на управление каналами.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        ticket_author_id = 0
        pinned_tickets_category_id = 0
        logging_channel_id: int | None = None

        async with view.bot.uow.start() as session:
            ticket = await get_latest_user_ticket(
                session,
                guild_id=guild.id,
                channel_id=channel.id,
            )

            if ticket is None:
                outcome = "ticket_not_found"
            elif ticket.state == TicketStateEnum.OPENED:
                outcome = "already_opened"
            elif ticket.state == TicketStateEnum.PINNED:
                outcome = "already_pinned"
            else:
                # Save ticket data
                ticket_author_id = ticket.author_id

                # Update ticket state to OPENED (not PINNED)
                ticket.state = TicketStateEnum.OPENED

                # Get pinned tickets category ID (ticket will be moved here and reopened)  # noqa: E501
                pinned_tickets_category_id = cast(
                    int,
                    await get_specified_channel(
                        session,
                        guild_id=guild.id,
                        config_type=GuildTicketsConfig,
                        channel_type=ChannelType.PINNED_TICKETS_CATEGORY,
                    ),
                )

                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_TICKETS,
                )

                outcome = "success"

        if outcome == "ticket_not_found":
            logger.warning(
                "No ticket found for user %s in guild %s",
                view.interaction_user_id,
                guild.id,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось открыть тикет",
                    "Тикет не найден для этого пользователя.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "already_opened":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось открыть тикет",
                    "Вы не можете открыть уже открытый тикет. Просто закрепите его.",  # noqa: E501
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "already_pinned":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось открыть тикет",
                    "Этот тикет уже закреплен другим модератором.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            # Get pinned tickets category
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
                        "Не удалось открыть тикет",
                        "Категория закрепленных тикетов настроена неправильно.",  # noqa: E501
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            # Update channel permissions to grant ticket author access
            ticket_author = await ensure_member_exists(guild, ticket_author_id)
            overwrites = channel.overwrites

            if ticket_author:
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
                    author_id=ticket_author_id,
                ),
            )

            # Dispatch event with OPENED state
            if logging_channel_id:
                view.bot.dispatch(
                    "ticket_changed",
                    data=TicketEventData(
                        guild,
                        channel.id,
                        ticket_author_id,
                        interaction.user.id,
                        TicketStateEnum.OPENED,
                        logging_channel_id,
                    ),
                )

            logger.info(
                "Ticket reopened by user %s in guild %s",
                interaction.user.id,
                guild.id,
            )

    @button(
        style=ButtonStyle.grey,
        label="Закрыть",
        emoji="<:lock4:1442914715025276988>",
        custom_id="ticket:close",
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def close_ticket(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["ManageTicketViewV2"],
    ):
        """Close the ticket."""

        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)
        user = cast(Member, interaction.user)

        await interaction.response.defer()

        if not guild.me.guild_permissions.manage_channels:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    "У меня нет прав на управление каналами.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        ticket_author_id = 0
        closed_tickets_category_id = 0
        logging_channel_id: int | None = None

        async with view.bot.uow.start() as session:
            ticket = await get_latest_user_ticket(
                session,
                guild_id=guild.id,
                channel_id=channel.id,
            )

            if ticket is None:
                outcome = "ticket_not_found"
            elif ticket.state == TicketStateEnum.CLOSED:
                outcome = "already_closed"
            else:
                # Save ticket data
                ticket_author_id = ticket.author_id

                # Update ticket state to CLOSED
                ticket.moderator_id = user.id
                ticket.state = TicketStateEnum.CLOSED

                # Get closed tickets category ID
                closed_tickets_category_id = cast(
                    int,
                    await get_specified_channel(
                        session,
                        guild_id=guild.id,
                        config_type=GuildTicketsConfig,
                        channel_type=ChannelType.CLOSED_TICKETS_CATEGORY,
                    ),
                )

                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_TICKETS,
                )

                outcome = "success"

        if outcome == "ticket_not_found":
            logger.warning(
                "No ticket found for user %s in guild %s",
                view.interaction_user_id,
                guild.id,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось закрыть тикет",
                    "Тикет не найден для этого пользователя.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "already_closed":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось закрыть тикет",
                    "Этот тикет уже закрыт.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
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
                        "Не удалось закрыть тикет",
                        "Категория закрытых тикетов не найдена.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            ticket_author = await ensure_member_exists(guild, ticket_author_id)
            overwrites = channel.overwrites

            if ticket_author:
                overwrites[ticket_author] = discord.PermissionOverwrite(
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
                    author_id=ticket_author_id,
                ),
            )

            # Dispatch event
            if logging_channel_id:
                view.bot.dispatch(
                    "ticket_changed",
                    data=TicketEventData(
                        guild,
                        channel.id,
                        ticket_author_id,
                        interaction.user.id,
                        TicketStateEnum.CLOSED,
                        logging_channel_id,
                    ),
                )

            logger.info(
                "Ticket closed by user %s in guild %s",
                interaction.user.id,
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

        self.clear_items()

        container = Container[Self](accent_color=Color.from_str("#515cff"))

        # Main text
        container.add_item(
            TextDisplay[Self](
                f"### Уважаемый <@{interaction_user_id}>, \nесли у вас есть жалобы на работу модераторов, пожалуйста, обратитесь на [форум Arz Guard](https://forum.arzguard.com)."  # noqa: E501
            )
        )

        # Action row
        container.add_item(Separator[Self]())
        container.add_item(ManageTicketButtons())
        container.add_item(Separator[Self]())

        # Footer
        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)} | <@&{ping_role_id}>"  # type: ignore  # noqa: E501
            )
        )

        self.add_item(container)
