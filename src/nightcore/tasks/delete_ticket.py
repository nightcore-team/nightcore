"""Task cog for deleting expired tickets."""

import asyncio
import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig, TicketState
from src.infra.db.operations import (
    get_specified_webhook,
    get_tickets_to_delete,
)
from src.utils._enums import ChannelType, TicketStateEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.tickets.events.dto import (
    TicketChangeEventData,
)
from src.nightcore.utils import ensure_guild_exists

logger = logging.getLogger(__name__)

MAX_CONCURRENT_PROCESSING = 5


class DeleteTicketTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot
        self._processing_semaphore = asyncio.Semaphore(
            MAX_CONCURRENT_PROCESSING
        )

        self.delete_ticket_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.delete_ticket_task.is_running():
            self.delete_ticket_task.cancel()

    @tasks.loop(hours=20)
    async def delete_ticket_task(self):
        """Task to delete tickets when their duration ends."""
        try:
            logger.info("[task] - Running delete ticket task")

            async with self.bot.uow.start() as session:
                closed_tickets = await get_tickets_to_delete(session)

            if not closed_tickets:
                logger.info("[task] - No closed tickets found")
                return

            processed = await self._process_tickets(closed_tickets)
            logger.info(
                "[task] - Completed delete ticket task: processed=%s",
                processed,
            )

        except Exception as e:
            logger.exception(
                "[task] - Error in delete ticket task iteration: %s",
                e,
                exc_info=True,
            )

    async def _process_tickets(self, tickets: list[TicketState]) -> int:
        """Process tickets with rate limiting."""
        tasks = []
        for ticket in tickets:
            tasks.append(self._process_single_with_limit(ticket))

        if not tasks:
            return 0

        results = await asyncio.gather(*tasks, return_exceptions=True)
        processed = 0
        for result in results:
            if result is True:
                processed += 1
            elif isinstance(result, Exception):
                logger.exception("[task] - Unexpected error processing ticket")

        return processed

    async def _process_single_with_limit(self, ticket: TicketState) -> bool:
        """Process a single ticket with semaphore limiting."""
        async with self._processing_semaphore:
            try:
                await self._process_single(ticket)
                return True
            except Exception:
                return False

    async def _process_single(self, ticket: TicketState) -> None:
        """Process a single ticket."""

        guild = await ensure_guild_exists(self.bot, ticket.guild_id)
        if guild is None:
            logger.info(
                "[task] - Guild %s not found",
                ticket.guild_id,
            )
            await self._delete_ticket(ticket)
            return

        async with self.bot.uow.start() as session:
            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_TICKETS,
            )

        self.bot.dispatch(
            "ticket_deleted",
            data=TicketChangeEventData(
                guild=guild,
                channel_id=ticket.channel_id,
                author_id=ticket.author_id,
                moderator_id=ticket.moderator_id,
                logging_webhook=logging_webhook,
                state=TicketStateEnum.DELETED,
            ),
        )

        try:
            async with self.bot.uow.start() as session:
                _ticket = await session.merge(ticket)
                _ticket.state = TicketStateEnum.DELETED

        except Exception as e:
            logger.exception(
                "[task] - Failed to delete ticket %s in guild %s: %s",
                ticket.id,
                ticket.guild_id,
                e,
            )
            return

        await self._delete_ticket(ticket)

        logger.info(
            "[task] - Deleted ticket in guild %s",
            ticket.guild_id,
        )

    async def _delete_ticket(self, ticket_state: TicketState) -> None:
        """Delete a ticket from the database."""
        async with self.bot.uow.start() as session:
            _ticket = await session.merge(ticket_state)
            await session.delete(_ticket)

    @delete_ticket_task.before_loop
    async def before_delete_ticket_task(self):
        """Prepare before starting the delete ticket task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @delete_ticket_task.error
    async def delete_ticket_task_error(self, exc: BaseException) -> None:
        """Handle errors in the delete ticket task."""
        logger.exception("[task] - Delete ticket task crashed:", exc_info=exc)

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.delete_ticket_task.is_running():
            logger.info("[task] - Restarting delete ticket task...")
            self.delete_ticket_task.restart()


async def setup(bot: "Nightcore"):
    """Setup the DeleteTicketTask cog."""
    await bot.add_cog(DeleteTicketTask(bot))
