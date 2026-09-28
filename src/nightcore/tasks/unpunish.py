"""Task cog for unpunishing users."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import get_expired_temp_infractions

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.infra.db.models import TempPunish
    from src.nightcore.bot import Nightcore

from src.nightcore.tasks.utils import handle_infraction_type_event

logger = logging.getLogger(__name__)

MAX_CONCURRENT_PROCESSING = 10


class UnPunishTask(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot
        self._processing_semaphore = asyncio.Semaphore(
            MAX_CONCURRENT_PROCESSING
        )

        self.un_punish_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.un_punish_task.is_running():
            self.un_punish_task.cancel()

    @tasks.loop(seconds=15)
    async def un_punish_task(self):
        """Task to unpunish users when their punishment duration ends."""
        await self.bot.task_manager.sleep(__name__)

        try:
            logger.info("[task] - Running unpunish task")

            async with self.bot.uow.start() as session:
                active_infractions = await get_expired_temp_infractions(
                    session
                )

            if not active_infractions:
                logger.info("[task] - No expired infractions found")
                return

            processed = await self._process_infractions(active_infractions)

            logger.info(
                "[task] - Completed unpunish task: processed=%s",
                processed,
            )

        except Exception as e:
            logger.exception(
                "[task] - Error in unpunish task iteration: %s",
                e,
                exc_info=True,
            )

    async def _process_infractions(
        self, infractions: Sequence[TempPunish]
    ) -> int:
        """Process infractions with rate limiting."""
        tasks: list[asyncio.Task[bool]] = []
        for infraction in infractions:
            tasks.append(
                asyncio.create_task(
                    self._process_single_with_limit(infraction)
                )
            )

        if not tasks:
            return 0

        results: list[bool | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        processed = 0
        for result in results:
            if result is True:
                processed += 1
            elif isinstance(result, Exception):
                logger.exception(
                    "[task] - Unexpected error processing infraction"
                )

        return processed

    async def _process_single_with_limit(self, infraction: TempPunish) -> bool:
        """Process a single infraction with semaphore limiting."""
        async with self._processing_semaphore:
            try:
                await self._process_single(infraction)
                return True
            except Exception:
                return False

    async def _process_single(self, infraction: TempPunish) -> None:
        """Process a single infraction - dispatch event after DB commit."""
        handle_infraction_type_event(active_punish=infraction, bot=self.bot)
        logger.info("[task] - Unpunished user: %s", infraction.user_id)

    @un_punish_task.before_loop
    async def before_un_punish_task(self):
        """Prepare before starting the unpunish task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @un_punish_task.error
    async def un_punish_task_error(self, exc: BaseException) -> None:
        """Handle errors in the unpunish task."""
        logger.exception("[task] - Unpunish task crashed:", exc_info=exc)

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.un_punish_task.is_running():
            logger.info("[task] - Restarting unpunish task...")
            self.un_punish_task.restart()


async def setup(bot: Nightcore):
    """Setup the UnPunishTask cog."""
    await bot.add_cog(UnPunishTask(bot))
