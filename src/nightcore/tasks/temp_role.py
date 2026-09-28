"""Task cog for deleting temp. roles from user."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from discord import Forbidden, HTTPException
from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import (
    delete_temp_roles,
    get_all_expired_temp_roles,
)
from src.nightcore.utils import (
    ensure_guild_exists,
    ensure_member_exists,
    ensure_role_exists,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.infra.db.models import TempRole
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)

MAX_CONCURRENT_REMOVES = 5


class DeleteTempRoleTask(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot
        self._remove_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REMOVES)

        self.delete_temp_role_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.delete_temp_role_task.is_running():
            self.delete_temp_role_task.cancel()

    @tasks.loop(seconds=60.0)
    async def delete_temp_role_task(self):
        """Task to delete temporary roles when their duration ends."""
        await self.bot.task_manager.sleep(__name__)

        try:
            logger.info("[task] - Running delete temp role task")

            async with self.bot.uow.start() as session:
                temp_roles = await get_all_expired_temp_roles(session)

            if not temp_roles:
                logger.info("[task] - No expired temp roles found")
                return

            removed = await self._remove_roles(temp_roles)

            async with self.bot.uow.start() as session:
                status_ids = [tr.id for tr in temp_roles]
                await delete_temp_roles(session, status_ids=status_ids)

            logger.info(
                "[task] - Completed temp role deletion: removed=%s",
                removed,
            )

        except Exception as e:
            logger.exception(
                "[task] - Error in delete temp role task iteration: %s",
                e,
                exc_info=True,
            )

    async def _remove_roles(self, temp_roles: Sequence[TempRole]) -> int:
        """Remove roles with rate limiting."""
        tasks: list[asyncio.Task[bool]] = []
        for tr in temp_roles:
            tasks.append(
                asyncio.create_task(
                    self._remove_role_with_limit(
                        tr.guild_id,
                        tr.user_id,
                        tr.role_id,
                    )
                )
            )

        if not tasks:
            return 0

        results: list[bool | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        removed = 0
        for result in results:
            if result is True:
                removed += 1
            elif isinstance(result, Exception):
                logger.exception(
                    "[task] - Unexpected error removing temp role"
                )

        return removed

    async def _remove_role_with_limit(
        self, guild_id: int, user_id: int, role_id: int
    ) -> bool:
        """Remove a single role with semaphore limiting."""
        async with self._remove_semaphore:
            try:
                await self._remove_role(guild_id, user_id, role_id)
                return True
            except Exception:
                return False

    async def _remove_role(
        self, guild_id: int, user_id: int, role_id: int
    ) -> None:
        """Remove a temporary role from a member."""

        guild = await ensure_guild_exists(self.bot, guild_id)
        if guild is None:
            logger.info(
                "[task] - Guild %s not found",
                guild_id,
            )
            return

        role = await ensure_role_exists(guild, role_id)
        if role is None:
            logger.info(
                "[task] - Role %s not found in guild %s",
                role_id,
                guild.id,
            )
            return

        member = await ensure_member_exists(guild, user_id)
        if member is None:
            logger.info(
                "[task] - Member %s not found in guild %s",
                user_id,
                guild.id,
            )
            return

        try:
            await member.remove_roles(role, reason="Temporary role expired")
        except (Forbidden, HTTPException) as e:
            logger.warning(
                "[task] - Failed to remove role %s from user %s: %s",
                role_id,
                user_id,
                e,
            )
            return

        logger.info(
            "[task] - Removed temporary role %s from member %s in guild %s",
            role_id,
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

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.delete_temp_role_task.is_running():
            logger.info("[task] - Restarting delete temp role task...")
            self.delete_temp_role_task.restart()


async def setup(bot: Nightcore):
    """Setup the DeleteTempRoleTask cog."""
    await bot.add_cog(DeleteTempRoleTask(bot))
