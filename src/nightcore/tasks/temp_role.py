"""Task cog for deleting temp. roles from user."""

import asyncio
import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import TempRole
from src.infra.db.operations import get_all_expired_temp_roles
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

    async def _delete_temp_role(self, temp_role: TempRole) -> None:
        """Delete a temporary role from the database."""
        async with self.bot.uow.start() as session:
            _temp_role = await session.merge(temp_role)
            await session.delete(_temp_role)

    @tasks.loop(seconds=60.0)
    async def delete_temp_role_task(self):
        """Task to delete temporary roles when their duration ends."""
        try:
            logger.info("[task] - Running delete temp role task")
            async with self.bot.uow.start() as session:
                temp_roles = await get_all_expired_temp_roles(session)
                if not temp_roles:
                    logger.info("[task] - No expired temp roles found")
                    return

            for temp_role in temp_roles:
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

                await member.remove_roles(
                    role, reason="Temporary role expired"
                )

                async with self.bot.uow.start() as session:
                    _temp_role = await session.merge(temp_role)
                    await session.delete(_temp_role)

                logger.info(
                    "[task] - Removed temporary role %s from member %s in guild %s",  # noqa: E501
                    temp_role.role_id,
                    member.id,
                    guild.id,
                )

        except Exception as e:
            logger.exception(
                "[task] - Error in delete temp role task iteration: %s",
                e,
                exc_info=True,
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

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.delete_temp_role_task.is_running():
            logger.info("[task] - Restarting delete temp role task...")
            self.delete_temp_role_task.restart()


async def setup(bot: "Nightcore"):
    """Setup the DeleteTempRoleTask cog."""
    await bot.add_cog(DeleteTempRoleTask(bot))
