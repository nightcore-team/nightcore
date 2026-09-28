"""Task cog for resetting temporary economy multipliers."""

import asyncio
import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildMultipliersConfig
from src.infra.db.operations import (
    delete_temp_multipliers,
    get_all_expired_temp_multipliers,
    get_specified_guild_config,
)
from src.utils._enums import MultiplierTypeEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class ResetTempMultiplierTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

        self.reset_temp_multiplier_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.reset_temp_multiplier_task.is_running():
            self.reset_temp_multiplier_task.cancel()

    @tasks.loop(minutes=1)
    async def reset_temp_multiplier_task(self):
        """Task to reset temporary multipliers when their duration ends."""
        await self.bot.task_manager.sleep(__name__)

        try:
            logger.info("[task] - Running reset temp multiplier task")

            async with self.bot.uow.start() as session:
                temp_multipliers = await get_all_expired_temp_multipliers(
                    session
                )

            if not temp_multipliers:
                logger.info("[task] - No expired temp multipliers found")
                return

            guild_ids = {tm.guild_id for tm in temp_multipliers}
            configs: dict[int, GuildMultipliersConfig] = {}

            async with self.bot.uow.start() as session:
                for guild_id in guild_ids:
                    config = await get_specified_guild_config(
                        session,
                        guild_id=guild_id,
                        config_type=GuildMultipliersConfig,
                    )
                    if config:
                        configs[guild_id] = config

            for temp_multiplier in temp_multipliers:
                guild_id = temp_multiplier.guild_id
                multiplier_type = temp_multiplier.multiplier_type

                config = configs.get(guild_id)
                if config is None:
                    continue

                match multiplier_type:
                    case MultiplierTypeEnum.EXP:
                        config.temp_exp_multiplier = None
                        logger.info(
                            "[task] - Reset EXP multiplier for guild %s",
                            guild_id,
                        )
                    case MultiplierTypeEnum.COINS:
                        config.temp_coins_multiplier = None
                        logger.info(
                            "[task] - Reset COINS multiplier for guild %s",
                            guild_id,
                        )
                    case MultiplierTypeEnum.BATTLEPASS:
                        config.temp_battlepass_multiplier = None
                        logger.info(
                            "[task] - Reset BATTLEPASS multiplier "
                            "for guild %s",
                            guild_id,
                        )

            async with self.bot.uow.start() as session:
                status_ids = [tm.id for tm in temp_multipliers]
                await delete_temp_multipliers(session, status_ids=status_ids)

                for temp_multiplier in temp_multipliers:
                    logger.info(
                        "[task] - Removed expired %s multiplier "
                        "(x%s) for guild %s",
                        temp_multiplier.multiplier_type.value,
                        temp_multiplier.multiplier,
                        temp_multiplier.guild_id,
                    )

        except Exception as e:
            logger.exception(
                "[task] - Error in reset temp multiplier task iteration: %s",
                e,
                exc_info=True,
            )

    @reset_temp_multiplier_task.before_loop
    async def before_reset_temp_multiplier_task(self):
        """Prepare before starting the reset temp multiplier task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @reset_temp_multiplier_task.error
    async def reset_temp_multiplier_task_error(self, exc: BaseException):
        """Handle errors in the reset temp multiplier task."""
        logger.exception(
            "[task] - Reset temp multiplier task crashed:",
            exc_info=exc,
        )

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.reset_temp_multiplier_task.is_running():
            logger.info("[task] - Restarting reset temp multiplier task...")
            self.reset_temp_multiplier_task.restart()


async def setup(bot: "Nightcore"):
    """Setup the ResetTempMultiplierTask cog."""
    await bot.add_cog(ResetTempMultiplierTask(bot))
