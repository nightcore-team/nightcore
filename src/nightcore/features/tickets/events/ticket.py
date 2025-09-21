"""Ticket Event Cog for Nightcore Bot."""

import asyncio
import io
import logging
from collections.abc import Awaitable

import discord
from chat_exporter import export  # type: ignore
from discord.ext.commands import Cog  # type: ignore

from src.nightcore.bot import Nightcore

# TODO: вынести в глобальные утилиты (сед модер лог).
from src.nightcore.features.moderation.utils import send_moderation_log
from src.nightcore.features.tickets.events.dto import TicketEventData
from src.nightcore.features.tickets.utils import CustomAttachmentsHandler
from src.nightcore.utils import ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


class TicketEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_ticket_changed(self, *, data: TicketEventData) -> None:
        """Handle ticket change events."""
        # get logging channel
        # check if channel exists
        # send log to logging channel

        logger.info(
            "[event] on_ticket_changed - %s: Guild: %s, Member: %s, Moderator: %s",  # noqa: E501
            data.state.value,
            data.guild.id,
            data.author_id,
            data.moderator_id,
        )

        gather_list: list[Awaitable[None]] = []

        if data.logging_channel_id:
            gather_list.append(
                send_moderation_log(
                    self.bot,
                    channel_id=data.logging_channel_id,
                    event_data=data,
                )
            )
        else:
            logger.warning(
                "[event] on_ticket_changed - Guild: %s, logging channel is not set",  # noqa: E501
                data.guild.id,
            )
            return

        try:
            await asyncio.gather(*gather_list, return_exceptions=True)
        except Exception as e:
            logger.exception(
                "[event] on_ticket_changed - %s: Failed to send log message: %s",  # noqa: E501
                data.state.value,
                e,
            )

    @Cog.listener()
    async def on_ticket_deleted(self, data: TicketEventData) -> None:
        """Called when a ticket is deleted."""
        logger.info(
            "[event] on_ticket_deleted - %s: Guild: %s, Member: %s, Moderator: %s",  # noqa: E501
            data.state.value,
            data.guild.id,
            data.author_id,
            data.moderator_id,
        )

        ticket_channel = await ensure_messageable_channel_exists(
            data.guild, data.channel_id
        )
        if not ticket_channel:
            logger.error(
                "[event] on_ticket_deleted - Guild: %s, Channel: %s not found",
                data.guild.id,
                data.channel_id,
            )
            return

        handler = CustomAttachmentsHandler(
            channel=ticket_channel,  # type: ignore
        )

        transcript = await export(
            channel=ticket_channel,
            attachment_handler=handler.handler,
        )

        transcript_file = discord.File(
            fp=io.BytesIO(transcript.encode()),
            filename=f"ticket-{data.channel_id}-transcript.html",
        )

        gather_list: list[Awaitable[None]] = []
        # TODO: fix it
        if data.logging_channel_id:
            gather_list.append(
                send_moderation_log(
                    self.bot,
                    channel_id=data.logging_channel_id,
                    event_data=data,
                    attachments=[transcript_file],
                )
            )
        else:
            logger.warning(
                "[event] on_ticket_deleted - Guild: %s, logging channel is not set",  # noqa: E501
                data.guild.id,
            )
            return

        try:
            await asyncio.gather(*gather_list, return_exceptions=True)
        except Exception as e:
            logger.exception(
                "[event] on_ticket_deleted - %s: Failed to send log message: %s",  # noqa: E501
                data.state.value,
                e,
            )


async def setup(bot: Nightcore):
    """Setup the TicketEvent cog."""
    await bot.add_cog(TicketEvent(bot))
