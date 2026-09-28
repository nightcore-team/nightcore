"""Task cog for deleting expired VIP statuses."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import (
    delete_user_vip_statuses,
    get_expired_user_vip_statuses_for_update,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


class ExpireVipTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

        self.expire_vip_task.start()

    async def cog_unload(self) -> None:
        """Cancel the task when the cog unloads."""
        if self.expire_vip_task.is_running():
            self.expire_vip_task.cancel()

    @tasks.loop(minutes=5)
    async def expire_vip_task(self) -> None:
        """Delete VIP statuses that passed their expiry date."""
        await self.bot.task_manager.sleep(__name__)

        try:
            async with self.bot.uow.start() as session:
                expired = await get_expired_user_vip_statuses_for_update(
                    session,
                    now=datetime.now(UTC),
                )

                if not expired:
                    return

                # the rows are locked with skip_locked, so a grant that is
                # extending one of them right now is never touched
                await delete_user_vip_statuses(
                    session,
                    status_ids=[status.id for status in expired],
                )

                logger.info(
                    "[task] - Deleted %s expired VIP statuses",
                    len(expired),
                )

        except Exception:
            logger.exception("[task] - Failed to delete expired VIP statuses")

    @expire_vip_task.before_loop
    async def before_expire_vip_task(self) -> None:
        """Wait until the bot is ready before starting the task."""
        await self.bot.wait_until_ready()


async def setup(bot: "Nightcore") -> None:
    """Setup the expired VIP statuses task."""
    await bot.add_cog(ExpireVipTask(bot))
