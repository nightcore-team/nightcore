"""Task cog for cycling rainbow role colors."""

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Final

import discord
from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import (
    get_due_rainbow_roles,
    update_rainbow_role_schedule,
)
from src.nightcore.utils import (
    ensure_guild_exists,
    ensure_role_exists,
)
from src.utils._enums import RainbowColorChangeTypeEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)

CHANGE_MIN_INTERVAL: Final[int] = 30 * 60
CHANGE_MAX_INTERVAL: Final[int] = 120 * 60
PALETTE_SIZE: Final[int] = 12
MIN_HUE_SEPARATION: Final[float] = 0.12
RANDOM_ATTEMPTS: Final[int] = 10

_RAINBOW_PALETTE = [
    discord.Color.from_hsv(i / PALETTE_SIZE, 1.0, 1.0)
    for i in range(PALETTE_SIZE)
]


class RainbowRoleTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

        self.rainbow_role_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.rainbow_role_task.is_running():
            self.rainbow_role_task.cancel()

    @staticmethod
    def _random_hue_pair() -> tuple[float, float]:
        """Return two rainbow hues with a visible separation for a gradient."""
        hue1 = random.random()

        for _ in range(RANDOM_ATTEMPTS):
            hue2 = random.random()
            diff = abs(hue2 - hue1)
            if min(diff, 1.0 - diff) >= MIN_HUE_SEPARATION:
                return hue1, hue2

        return hue1, (hue1 + 0.5) % 1.0

    @staticmethod
    async def _apply_color(
        role: discord.Role,
        primary: discord.Color,
        secondary: discord.Color | None = None,
    ) -> bool:
        """Apply a color to a role, falling back to solid if a gradient fails."""  # noqa: E501
        if secondary is not None:
            try:
                await role.edit(
                    color=primary,
                    secondary_color=secondary,
                    reason="Rainbow role color cycle",
                )
                return True
            except (discord.Forbidden, discord.HTTPException) as e:
                logger.warning(
                    "[task] Gradient not available for role %s in guild %s: %s. Falling back to solid color.",  # noqa: E501
                    role.id,
                    role.guild.id,
                    e,
                )

        try:
            await role.edit(
                color=primary,
                secondary_color=None,
                reason="Rainbow role color cycle",
            )
            return True
        except Exception as e:
            logger.exception(
                "[task] Failed to update rainbow role %s in guild %s: %s",
                role.id,
                role.guild.id,
                e,
            )
            return False

    @tasks.loop(seconds=180)
    async def rainbow_role_task(self):
        """Task to cycle rainbow role colors."""
        try:
            now = datetime.now(UTC)

            async with self.bot.uow.start(readonly=True) as session:
                due_roles = await get_due_rainbow_roles(session, now=now)

            if not due_roles:
                logger.info("[task] - No due rainbow roles")
                return

            updates: dict[int, tuple[datetime, int | None]] = {}

            for rainbow in due_roles:
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

                if rainbow.change_type == RainbowColorChangeTypeEnum.RANDOM:
                    hue1, hue2 = RainbowRoleTask._random_hue_pair()

                    primary = discord.Color.from_hsv(hue1, 1.0, 1.0)
                    secondary = discord.Color.from_hsv(hue2, 1.0, 1.0)
                    next_step = None
                else:
                    step = (
                        rainbow.current_step
                        if rainbow.current_step is not None
                        else role.id % PALETTE_SIZE
                    )

                    primary = _RAINBOW_PALETTE[step]
                    secondary = None
                    next_step = (step + 1) % PALETTE_SIZE

                if not await RainbowRoleTask._apply_color(
                    role, primary, secondary
                ):
                    continue

                updates[rainbow.guild_id] = (
                    now
                    + timedelta(
                        seconds=random.randint(
                            CHANGE_MIN_INTERVAL, CHANGE_MAX_INTERVAL
                        )
                    ),
                    next_step,
                )

                logger.info(
                    "[task] - Updated rainbow role %s in guild %s (type=%s)",
                    rainbow.role_id,
                    guild.id,
                    rainbow.change_type.value,
                )

            if updates:
                async with self.bot.uow.start() as session:
                    for guild_id, (
                        next_change_at,
                        next_step,
                    ) in updates.items():
                        await update_rainbow_role_schedule(
                            session,
                            guild_id=guild_id,
                            next_change_at=next_change_at,
                            current_step=next_step,
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
