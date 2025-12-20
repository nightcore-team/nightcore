"""Task cog for unpunishing users."""

import logging
from datetime import UTC, datetime, timedelta

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.config.config import config
from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType, TicketStateEnum
from src.infra.db.operations import (
    get_all_closed_tickets,
    get_specified_channel,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.tickets.events.dto import TicketEventData
from src.nightcore.utils import ensure_guild_exists

logger = logging.getLogger(__name__)


# CRITICAL
class DeleteTicketTask(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

        self.delete_ticket_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.delete_ticket_task.is_running():
            self.delete_ticket_task.cancel()

    @tasks.loop(minutes=30)
    async def delete_ticket_task(self):
        """Task to delete tickets when their duration ends."""
        logger.info("[task] - Running delete ticket task")
        async with self.bot.uow.start() as session:
            closed_tickets = await get_all_closed_tickets(session)

            for ticket in closed_tickets:
                if ticket.is_deleted:
                    continue
                if not ticket.updated_at + timedelta(
                    hours=config.bot.CLOSED_TICKET_ALIVE_HOURS
                ) <= datetime.now(UTC):
                    continue

                guild = await ensure_guild_exists(self.bot, ticket.guild_id)
                if guild is None:
                    logger.error(
                        "[task] - Guild %s not found",
                        ticket.guild_id,
                    )
                    continue

                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_TICKETS,
                )

                self.bot.dispatch(
                    "ticket_deleted",
                    data=TicketEventData(
                        guild=guild,
                        channel_id=ticket.channel_id,
                        author_id=ticket.author_id,
                        moderator_id=ticket.moderator_id,
                        logging_channel_id=logging_channel_id,
                        state=TicketStateEnum.DELETED,
                    ),
                )

                ticket.is_deleted = True

                logger.info(
                    "[task] - Deleted ticket in guild %s",
                    ticket.guild_id,
                )

    @delete_ticket_task.before_loop
    async def before_delete_ticket_task(self):
        """Prepare before starting the delete ticket task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @delete_ticket_task.error
    async def delete_ticket_task_error(self, exc):  # type: ignore
        """Handle errors in the delete ticket task."""
        logger.exception("[task] - Delete ticket task crashed:", exc_info=exc)  # type: ignore
        raise exc


async def setup(bot: Nightcore):
    """Setup the DeleteTicketTask cog."""
    await bot.add_cog(DeleteTicketTask(bot))
