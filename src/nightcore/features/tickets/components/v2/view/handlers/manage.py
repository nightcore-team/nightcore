"""Ticket manage button handlers."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import discord
from discord import CategoryChannel, Guild, Member, TextChannel
from discord.interactions import Interaction

from src.nightcore.utils.lock_manager import AsyncioLockTypeEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models import GuildLoggingConfig, GuildTicketsConfig
from src.infra.db.models.discord_webhook import DiscordWebhook
from src.infra.db.operations import (
    get_specified_channel,
    get_specified_webhook,
    get_ticket_state,
)
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    MissingPermissionsViewV2,
)
from src.nightcore.features.tickets.events.dto import TicketChangeEventData
from src.nightcore.utils import ensure_messageable_channel_exists
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import ChannelType, TicketStateEnum

logger = logging.getLogger(__name__)


@check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)
async def handle_ticket_pin_button(
    interaction: Interaction["Nightcore"],
) -> None:
    """Pin the ticket."""

    from ..manage_ticket import TicketStateViewV2

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    channel = cast(TextChannel, interaction.channel)
    user = cast(Member, interaction.user)

    await interaction.response.defer()

    if not guild.me.guild_permissions.manage_channels:
        await interaction.followup.send(
            view=MissingPermissionsViewV2(
                "У меня нет прав на управление каналами.",
            ),
            ephemeral=True,
        )
        return

    outcome = ""
    ticket_author_id = 0
    pinned_tickets_category_id = 0
    logging_webhook: DiscordWebhook | None = None

    async with (
        bot.lock_manager.acquire(
            AsyncioLockTypeEnum.TicketManageAction, channel.id
        ),
        bot.uow.start() as session,
    ):
        ticket_state = await get_ticket_state(
            session, guild_id=guild.id, channel_id=channel.id
        , for_update=True)

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
            ticket_state.updated_at = datetime.now(UTC)

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

            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_TICKETS,
            )

            outcome = "success"

    if outcome == "ticket_not_found":
        logger.warning(
            "No ticket found for user %s in guild %s",
            interaction.user.id,
            guild.id,
        )
        await interaction.followup.send(
            view=ErrorViewV2(
                "Не удалось закрепить тикет",
                "Тикет не найден для этого пользователя.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "ticket_closed":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Не удалось закрепить тикет",
                "Вы не можете закрепить закрытый тикет.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "already_pinned":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Не удалось закрепить тикет",
                "Этот тикет уже закреплен.",
            ),
            ephemeral=True,
        )
        return

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
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось закрепить тикет",
                    "Категория закрепленных тикетов не найдена.",
                ),
                ephemeral=True,
            )
            return

        await channel.edit(
            category=cast(CategoryChannel, pinned_tickets_category),
        )

        await interaction.followup.send(
            view=TicketStateViewV2(
                bot=bot,
                state=TicketStateEnum.PINNED,
                moderator_id=interaction.user.id,
                author_id=ticket_author_id,
            ),
        )

        # Dispatch event
        if logging_webhook:
            bot.dispatch(
                "ticket_changed",
                data=TicketChangeEventData(
                    guild,
                    channel.id,
                    ticket_author_id,
                    interaction.user.id,
                    TicketStateEnum.PINNED,
                    logging_webhook,
                ),
            )

        logger.info(
            "Ticket pinned by user %s in guild %s",
            interaction.user.id,
            guild.id,
        )


@check_required_permissions(PermissionsFlagEnum.HEAD_MODERATION_ACCESS)
async def handle_ticket_reopen_button(
    interaction: Interaction["Nightcore"],
) -> None:
    """Reopen the ticket."""

    from ..manage_ticket import TicketStateViewV2

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    channel = cast(TextChannel, interaction.channel)

    await interaction.response.defer()

    if not guild.me.guild_permissions.manage_channels:
        await interaction.followup.send(
            view=MissingPermissionsViewV2(
                "У меня нет прав на управление каналами.",
            ),
            ephemeral=True,
        )
        return

    outcome = ""
    ticket_author_id = 0
    pinned_tickets_category_id = 0
    logging_webhook: DiscordWebhook | None = None

    async with (
        bot.lock_manager.acquire(
            AsyncioLockTypeEnum.TicketManageAction, channel.id
        ),
        bot.uow.start() as session,
    ):
        ticket = await get_ticket_state(
            session,
            guild_id=guild.id,
            channel_id=channel.id,
         for_update=True)

        if ticket is None:
            outcome = "ticket_not_found"
        elif ticket.state == TicketStateEnum.OPENED:
            outcome = "already_opened"
        elif ticket.state == TicketStateEnum.PINNED:
            outcome = "already_pinned"
        else:
            # Save ticket data
            ticket_author_id = ticket.author_id

            # Update ticket state to PINNED
            ticket.state = TicketStateEnum.PINNED
            ticket.updated_at = datetime.now(UTC)

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

            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_TICKETS,
            )

            outcome = "success"

    if outcome == "ticket_not_found":
        logger.warning(
            "No ticket found for user %s in guild %s",
            ticket_author_id,
            guild.id,
        )
        await interaction.followup.send(
            view=ErrorViewV2(
                "Не удалось открыть тикет",
                "Тикет не найден для этого пользователя.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "already_opened":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Не удалось открыть тикет",
                "Вы не можете открыть уже открытый тикет. ",
            ),
            ephemeral=True,
        )
        return

    if outcome == "already_pinned":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Не удалось открыть тикет",
                "Этот тикет уже закреплен другим модератором.",
            ),
            ephemeral=True,
        )
        return

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
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось открыть тикет",
                    "Категория закрепленных тикетов настроена неправильно.",
                ),
                ephemeral=True,
            )
            return

        overwrites = channel.overwrites

        overwrites[guild.default_role] = discord.PermissionOverwrite(
            read_messages=True,
            send_messages=True,
            attach_files=True,
            read_message_history=True,
            view_channel=False,
        )

        await channel.edit(
            category=cast(CategoryChannel, pinned_tickets_category),
            overwrites=overwrites,
        )

        await interaction.followup.send(
            view=TicketStateViewV2(
                bot=bot,
                state=TicketStateEnum.OPENED,
                moderator_id=interaction.user.id,
                author_id=ticket_author_id,
            ),
        )

        # Dispatch event with OPENED state
        if logging_webhook:
            bot.dispatch(
                "ticket_changed",
                data=TicketChangeEventData(
                    guild,
                    channel.id,
                    ticket_author_id,
                    interaction.user.id,
                    TicketStateEnum.OPENED,
                    logging_webhook,
                ),
            )

        logger.info(
            "Ticket reopened by user %s in guild %s",
            interaction.user.id,
            guild.id,
        )


@check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)
async def handle_ticket_close_button(
    interaction: Interaction["Nightcore"],
) -> None:
    """Close the ticket."""

    from ..manage_ticket import TicketStateViewV2

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    channel = cast(TextChannel, interaction.channel)
    user = cast(Member, interaction.user)

    await interaction.response.defer()

    if not guild.me.guild_permissions.manage_channels:
        await interaction.followup.send(
            view=MissingPermissionsViewV2(
                "У меня нет прав на управление каналами.",
            ),
            ephemeral=True,
        )
        return

    outcome = ""
    ticket_author_id = 0
    closed_tickets_category_id = 0
    logging_webhook: DiscordWebhook | None = None

    async with (
        bot.lock_manager.acquire(
            AsyncioLockTypeEnum.TicketManageAction, channel.id
        ),
        bot.uow.start() as session,
    ):
        ticket = await get_ticket_state(
            session,
            guild_id=guild.id,
            channel_id=channel.id,
         for_update=True)

        if ticket is None:
            outcome = "ticket_not_found"
        elif ticket.state == TicketStateEnum.CLOSED:
            outcome = "already_closed"
        else:
            # Save ticket data
            ticket_author_id = ticket.author_id

            # Update ticket state to CLOSED
            ticket.state = TicketStateEnum.CLOSED
            ticket.updated_at = datetime.now(UTC)

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

            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_TICKETS,
            )

            outcome = "success"

    if outcome == "ticket_not_found":
        logger.warning(
            "No ticket found for user %s in guild %s",
            interaction.user.id,
            guild.id,
        )
        await interaction.followup.send(
            view=ErrorViewV2(
                "Не удалось закрыть тикет",
                "Тикет не найден для этого пользователя.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "already_closed":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Не удалось закрыть тикет",
                "Этот тикет уже закрыт.",
            ),
            ephemeral=True,
        )
        return

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
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось закрыть тикет",
                    "Категория закрытых тикетов не найдена.",
                ),
                ephemeral=True,
            )
            return

        overwrites = channel.overwrites

        overwrites[guild.default_role] = discord.PermissionOverwrite(
            send_messages=False,
            view_channel=False,
        )

        await channel.edit(
            category=cast(CategoryChannel, closed_tickets_category),
            overwrites=overwrites,
        )

        await interaction.followup.send(
            view=TicketStateViewV2(
                bot=bot,
                state=TicketStateEnum.CLOSED,
                moderator_id=interaction.user.id,
                author_id=ticket_author_id,
            ),
        )

        # Dispatch event
        if logging_webhook:
            bot.dispatch(
                "ticket_changed",
                data=TicketChangeEventData(
                    guild,
                    channel.id,
                    ticket_author_id,
                    user.id,
                    TicketStateEnum.CLOSED,
                    logging_webhook,
                ),
            )

        logger.info(
            "Ticket closed by user %s in guild %s",
            interaction.user.id,
            guild.id,
        )
