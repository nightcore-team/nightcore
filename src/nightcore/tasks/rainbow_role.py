"""Task cog for cycling rainbow role colors."""

import asyncio
import logging
import random
import time
from typing import TYPE_CHECKING, Final

import discord
from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import get_all_rainbow_roles
from src.nightcore.utils import (
    ensure_guild_exists,
    ensure_role_exists,
)
from src.utils._enums import RainbowColorChangeTypeEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)

RAINBOW_INTERVAL_SECONDS: Final[float] = 1800.0
RAINBOW_STEPS: Final[int] = 20


class RainbowRoleTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

        self.rainbow_role_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.rainbow_role_task.is_running():
            self.rainbow_role_task.cancel()

    @staticmethod
    def _current_hue() -> float:
        """Compute the current rainbow hue step from the wall clock."""
        step = int(time.time() // RAINBOW_INTERVAL_SECONDS) % RAINBOW_STEPS
        return step / RAINBOW_STEPS

    @staticmethod
    def _hue_for_change_type(
        change_type: RainbowColorChangeTypeEnum,
    ) -> float:
        """Compute the hue for the given rainbow change type."""
        if change_type == RainbowColorChangeTypeEnum.RANDOM:
            return random.random()

        return RainbowRoleTask._current_hue()

    @tasks.loop(seconds=RAINBOW_INTERVAL_SECONDS)
    async def rainbow_role_task(self):
        """Task to cycle rainbow role colors."""
        try:
            async with self.bot.uow.start(readonly=True) as session:
                rainbow_roles = await get_all_rainbow_roles(session)

            if not rainbow_roles:
                logger.info("[task] - No rainbow roles configured")
                return

            for rainbow in rainbow_roles:
                guild = await ensure_guild_exists(self.bot, rainbow.guild_id)
                if guild is None:
                    logger.info(
                        "[task] - Guild %s not found, skipping",
                        rainbow.guild_id,
                    )
                    continue

                role = await ensure_role_exists(guild, rainbow.role_id)
                if role is None:
                    logger.info(
                        "[task] - Role %s not found in guild %s, skipping",
                        rainbow.role_id,
                        guild.id,
                    )
                    continue

                hue = self._hue_for_change_type(rainbow.change_type)

                try:
                    await role.edit(
                        color=discord.Color.from_hsv(hue, 1.0, 1.0),
                        reason="Rainbow role color cycle",
                    )
                except Exception as e:
                    logger.exception(
                        "[task] - Failed to update rainbow role %s in guild %s: %s",  # noqa: E501
                        rainbow.role_id,
                        guild.id,
                        e,
                    )
                    continue

                logger.info(
                    "[task] - Updated rainbow role %s in guild %s to hue %.2f (type=%s)",  # noqa: E501
                    rainbow.role_id,
                    guild.id,
                    hue,
                    rainbow.change_type.value,
                )

        except Exception as e:
            logger.exception(
                "[task] - Error in rainbow role task iteration: %s",
                e,
                exc_info=True,
            )

    @rainbow_role_task.before_loop
    async def before_rainbow_role_task(self):
        """Prepare before starting the rainbow role task."""
        logger.debug("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @rainbow_role_task.error
    async def rainbow_role_task_error(self, exc):  # type: ignore
        """Handle errors in the rainbow role task."""
        logger.exception(
            "[task] - Rainbow role task crashed:",
            exc_info=exc,  # type: ignore
        )

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.rainbow_role_task.is_running():
            logger.info("[task] - Restarting rainbow role task...")
            self.rainbow_role_task.restart()


async def setup(bot: "Nightcore"):
    """Setup the RainbowRoleTask cog."""
    await bot.add_cog(RainbowRoleTask(bot))
