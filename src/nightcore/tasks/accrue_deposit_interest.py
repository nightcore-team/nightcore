"""Accrue deposit interest task."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import accrue_deposit_interest_for_guild

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class AccrueDepositInterestTask(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

        self.accrue_deposit_interest_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.accrue_deposit_interest_task.is_running():
            self.accrue_deposit_interest_task.cancel()

    @tasks.loop(hours=1)
    async def accrue_deposit_interest_task(self):
        """Accrue deposit interest task."""

        await self.bot.task_manager.sleep(__name__)

        guilds = self.bot.guilds

        logger.info("[task] - Running accrue deposit interest task")

        try:
            for guild in guilds:
                # Separate transaction per guild for better performance
                async with self.bot.uow.start() as session:
                    updated = await accrue_deposit_interest_for_guild(
                        session, guild_id=guild.id
                    )

                logger.info(
                    "[task] - Accrued deposit interest for %s deposits "
                    "in guild %s",
                    updated,
                    guild.id,
                )

        except Exception as e:
            logger.exception(
                "[task] - Error in accrue deposit interest iteration: %s",
                e,
                exc_info=True,
            )

    @accrue_deposit_interest_task.before_loop
    async def before_check_forum_task(self):
        """Prepare before starting the accrue deposit interest task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @accrue_deposit_interest_task.error
    async def check_forum_task_error(self, exc: BaseException):  # type: ignore
        """Handle errors in the accrue deposit interest task."""
        logger.exception(
            "[task] - Accrue deposit interest task crashed:", exc_info=exc
        )

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.accrue_deposit_interest_task.is_running():
            logger.info("[task] - Restarting accrue deposit interest task...")
            self.accrue_deposit_interest_task.restart()


async def setup(bot: Nightcore):
    """Setup the AccrueDepositInterestTask cog."""
    await bot.add_cog(AccrueDepositInterestTask(bot))
