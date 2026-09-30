"""Task cog for deleting expired VIP statuses."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord import Forbidden, HTTPException
from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.loads import user_load_vip_status_vip
from src.infra.db.operations import (
    delete_user_vip_statuses,
    get_expired_user_vip_statuses_for_update,
)
from src.nightcore.utils import (
    ensure_guild_exists,
    ensure_member_exists,
    ensure_role_exists,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Sequence

    from src.infra.db.models.user import UserVipStatus
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)

BATCH_SIZE = 500
MAX_CONCURRENT_REVOKES = 5


class ExpireVipTask(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot
        self._revoke_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REVOKES)

        self.expire_vip_task.start()

    async def cog_unload(self) -> None:
        """Cancel the task when the cog unloads."""
        if self.expire_vip_task.is_running():
            self.expire_vip_task.cancel()

    @tasks.loop(minutes=10)
    async def expire_vip_task(self) -> None:
        """Delete VIP statuses that passed their expiry date."""
        await self.bot.task_manager.sleep(__name__)

        now = datetime.now(UTC)
        total_deleted = 0
        total_revoked = 0

        while True:
            async with self.bot.uow.start() as session:
                expired = await get_expired_user_vip_statuses_for_update(
                    session,
                    now=now,
                    options=[user_load_vip_status_vip],
                    limit=BATCH_SIZE,
                )

                if not expired:
                    break

                status_ids = [status.id for status in expired]

                await delete_user_vip_statuses(session, status_ids=status_ids)

                total_deleted += len(expired)

                logger.info(
                    "[task] - Deleted %s expired VIP statuses (batch)",
                    len(expired),
                )

            revoked = await self._revoke_roles(expired)
            total_revoked += revoked

        if total_deleted > 0:
            logger.info(
                "[task] - Completed expiry cycle: "
                "deleted=%s, roles_revoked=%s",
                total_deleted,
                total_revoked,
            )

    async def _revoke_roles(
        self, expired_statuses: Sequence[UserVipStatus]
    ) -> int:
        """Revoke roles for expired statuses with rate limiting."""
        tasks: list[Awaitable[bool]] = []

        for status in expired_statuses:
            if status.vip.role_id is not None:
                tasks.append(
                    self._revoke_role_with_limit(
                        status.guild_id,
                        status.user.user_id,
                        status.vip.role_id,
                    )
                )

        if not tasks:
            return 0

        results = await asyncio.gather(*tasks, return_exceptions=True)
        revoked = 0
        for result in results:
            if result is True:
                revoked += 1
            elif isinstance(result, Exception):
                logger.exception("[task] - Unexpected error revoking role")

        return revoked

    async def _revoke_role_with_limit(
        self, guild_id: int, user_id: int, role_id: int
    ) -> bool:
        """Revoke a single role with semaphore limiting."""
        async with self._revoke_semaphore:
            try:
                await self._revoke_role(guild_id, user_id, role_id)
                return True
            except Exception:
                return False

    async def _revoke_role(
        self, guild_id: int, user_id: int, role_id: int
    ) -> None:
        """Take the expired VIP's role away, logging and moving on on failure."""  # noqa: E501

        guild = await ensure_guild_exists(self.bot, guild_id)
        if guild is None:
            logger.warning(
                "[task] - Guild %s not found, skipped revoking role %s from %s",  # noqa: E501
                guild_id,
                role_id,
                user_id,
            )
            return

        role = await ensure_role_exists(guild, role_id)
        member = await ensure_member_exists(guild, user_id)

        if role is None or member is None:
            logger.warning(
                "[task] - Role %s or member %s not found in guild %s, skipped",
                role_id,
                user_id,
                guild_id,
            )
            return

        if role not in member.roles:
            return

        try:
            await member.remove_roles(
                role,
                reason="Срок действия VIP-статуса истёк.",
            )
        except (Forbidden, HTTPException) as error:
            logger.warning(
                "[task] - Failed to remove role %s from user %s: %s",
                role_id,
                user_id,
                error,
            )
            return

        logger.info(
            "[task] - Revoked role %s from user %s after VIP expiry",
            role_id,
            user_id,
        )

    @expire_vip_task.before_loop
    async def before_expire_vip_task(self) -> None:
        """Wait until the bot is ready before starting the task."""
        await self.bot.wait_until_ready()


async def setup(bot: Nightcore) -> None:
    """Setup the expired VIP statuses task."""
    await bot.add_cog(ExpireVipTask(bot))
