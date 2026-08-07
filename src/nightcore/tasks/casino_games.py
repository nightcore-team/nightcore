"""Task cog for ending casino games."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import get_active_casino_games
from src.nightcore.features.economy.utils.casino import GAME_FINALIZERS

if TYPE_CHECKING:
    from src.infra.db.models.casino import CasinoGame
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


class CasinoGamesTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

        self.end_casino_games_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.end_casino_games_task.is_running():
            self.end_casino_games_task.cancel()

    async def _process_game(self, game: "CasinoGame") -> None:
        """Process a single casino game through its registered finalizer."""
        finalizer = GAME_FINALIZERS[game.game_type]
        await finalizer(self.bot, game)

    @tasks.loop(seconds=15)
    async def end_casino_games_task(self):
        """End all expired casino games."""
        try:
            logger.info("[task] - Running end casino games task")

            async with self.bot.uow.start() as session:
                casino_games = await get_active_casino_games(
                    session,
                    dt=datetime.now(UTC),
                    game_types=list(GAME_FINALIZERS.keys()),
                )

            if not casino_games:
                logger.info("[task] - No casino games to end")
                return

            # Process each game in its own transaction
            for game in casino_games:
                await self._process_game(game)

        except Exception as e:
            logger.exception(
                "[task] - Error in end casino games task iteration: %s",
                e,
            )

    @end_casino_games_task.before_loop
    async def before_end_casino_games_task(self):
        """Prepare before starting the end casino games task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @end_casino_games_task.error
    async def end_casino_games_task_error(self, exc: BaseException) -> None:
        """Handle errors in the end casino games task."""
        logger.exception(
            "[task] - End casino games task crashed:",
            exc_info=exc,
        )

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.end_casino_games_task.is_running():
            logger.info("[task] - Restarting end casino games task...")
            self.end_casino_games_task.restart()


async def setup(bot: "Nightcore"):
    """Setup the CasinoGamesTask cog."""
    await bot.add_cog(CasinoGamesTask(bot))
