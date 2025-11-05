"""Task cog for resetting temporary economy multipliers."""

import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLevelsConfig
from src.infra.db.models._enums import MultiplierTypeEnum
from src.infra.db.operations import (
    get_all_expired_temp_multipliers,
    get_specified_guild_config,
)

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

    @tasks.loop(minutes=5.0)
    async def reset_temp_multiplier_task(self):
        """Task to reset temporary multipliers when their duration ends."""
        logger.info("[task] - Running reset temp multiplier task")

        async with self.bot.uow.start() as session:
            temp_multipliers = await get_all_expired_temp_multipliers(session)

            if not temp_multipliers:
                logger.info("[task] - No expired temp multipliers found")
                return

            for temp_multiplier in temp_multipliers:
                guild_id = temp_multiplier.guild_id
                multiplier_type = temp_multiplier.multiplier_type

                guild_config = await get_specified_guild_config(
                    session, guild_id=guild_id, config_type=GuildLevelsConfig
                )
                if guild_config is None:
                    logger.error(
                        "[task] - GuildLevelsConfig not found for guild %s",
                        guild_id,
                    )
                    continue

                match multiplier_type:
                    case MultiplierTypeEnum.EXP:
                        guild_config.temp_exp_multiplier = None
                        logger.info(
                            "[task] - Reset EXP multiplier for guild %s",
                            guild_id,
                        )
                    case MultiplierTypeEnum.COINS:
                        guild_config.temp_coins_multiplier = None
                        logger.info(
                            "[task] - Reset COINS multiplier for guild %s",
                            guild_id,
                        )

                await session.delete(temp_multiplier)

                logger.info(
                    "[task] - Removed expired %s multiplier (x%s) for guild %s",  # noqa: E501
                    multiplier_type.value,
                    temp_multiplier.multiplier,
                    guild_id,
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
        raise exc


async def setup(bot: "Nightcore"):
    """Setup the ResetTempMultiplierTask cog."""
    await bot.add_cog(ResetTempMultiplierTask(bot))
