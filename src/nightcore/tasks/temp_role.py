"""Task cog for deleting temp. roles from user."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import (
    get_all_temp_roles,
)
from src.nightcore.utils import (
    ensure_guild_exists,
    ensure_member_exists,
    ensure_role_exists,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class DeleteTempRoleTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

        self.delete_temp_role_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.delete_temp_role_task.is_running():
            self.delete_temp_role_task.cancel()

    @tasks.loop(seconds=60.0)
    async def delete_temp_role_task(self):
        """Task to delete temporary roles when their duration ends."""
        logger.debug("[task] - Running delete temp role task")
        async with self.bot.uow.start() as session:
            temp_roles = await get_all_temp_roles(session)

            for temp_role in temp_roles:
                if not temp_role.end_time <= datetime.now(UTC):
                    continue

                guild = await ensure_guild_exists(self.bot, temp_role.guild_id)
                if guild is None:
                    logger.warning(
                        "[task] - Guild %s not found",
                        temp_role.guild_id,
                    )
                    continue

                role = await ensure_role_exists(guild, temp_role.role_id)
                if role is None:
                    logger.warning(
                        "[task] - Role %s not found in guild %s",
                        temp_role.role_id,
                        guild.id,
                    )
                    continue

                member = await ensure_member_exists(guild, temp_role.user_id)
                if member is None:
                    logger.warning(
                        "[task] - Member %s not found in guild %s",
                        temp_role.user_id,
                        guild.id,
                    )
                    continue

                await asyncio.gather(
                    member.remove_roles(role, reason="Temporary role expired"),
                    session.delete(temp_role),
                )

                logger.debug(
                    "[task] - Removed temporary role %s from member %s in guild %s",
                    temp_role.role_id,
                    member.id,
                    guild.id,
                )

    @delete_temp_role_task.before_loop
    async def before_delete_temp_role_task(self):
        """Prepare before starting the delete temp role task."""
        logger.debug("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @delete_temp_role_task.error
    async def delete_temp_role_task_error(self, exc):  # type: ignore
        """Handle errors in the delete temp role task."""
        logger.exception(
            "[task] - Delete temp role task crashed:",
            exc_info=exc,  # type: ignore
        )
        raise exc


async def setup(bot: "Nightcore"):
    """Setup the DeleteTempRoleTask cog."""
    await bot.add_cog(DeleteTempRoleTask(bot))
