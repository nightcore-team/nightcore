"""Task cog for deleting expired role requests."""

import asyncio
import logging
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import RoleRequestState
from src.infra.db.operations import (
    get_role_requests_to_delete,
)
from src.utils._enums import RoleRequestStateEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.role_requests.components.v2.view import (
    CheckRoleRequestView,
    RoleRequestStateView,
)
from src.nightcore.utils import (
    ensure_guild_exists,
    ensure_message_exists,
    ensure_messageable_channel_exists,
)

logger = logging.getLogger(__name__)

MAX_CONCURRENT_PROCESSING = 5


class DeleteRoleRequestTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot
        self._processing_semaphore = asyncio.Semaphore(
            MAX_CONCURRENT_PROCESSING
        )

        self.delete_role_request_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.delete_role_request_task.is_running():
            self.delete_role_request_task.cancel()

    @tasks.loop(seconds=60.0)
    async def delete_role_request_task(self):
        """Task to delete role requests when their duration ends."""
        await self.bot.task_manager.sleep(__name__)

        try:
            logger.info("[task] - Running delete role request task")

            async with self.bot.uow.start() as session:
                all_rr = await get_role_requests_to_delete(session)

            if not all_rr:
                logger.info("[task] - No role requests to delete")
                return

            processed = await self._process_role_requests(all_rr)
            logger.info(
                "[task] - Completed role request deletion: processed=%s",
                processed,
            )

        except Exception as e:
            logger.exception(
                "[task] - Error in delete role request task iteration: %s",
                e,
                exc_info=True,
            )

    async def _process_role_requests(
        self, role_requests: list[RoleRequestState]
    ) -> int:
        """Process role requests with rate limiting."""
        tasks = []
        for rr in role_requests:
            tasks.append(self._process_single_with_limit(rr))

        if not tasks:
            return 0

        results = await asyncio.gather(*tasks, return_exceptions=True)
        processed = 0
        for result in results:
            if result is True:
                processed += 1
            elif isinstance(result, Exception):
                logger.exception(
                    "[task] - Unexpected error processing role request"
                )

        return processed

    async def _process_single_with_limit(self, rr: RoleRequestState) -> bool:
        """Process a single role request with semaphore limiting."""
        async with self._processing_semaphore:
            try:
                await self._process_single(rr)
                return True
            except Exception:
                return False

    async def _process_single(self, rr: RoleRequestState) -> None:
        """Process a single role request."""

        guild = await ensure_guild_exists(self.bot, rr.guild_id)
        if not guild:
            logger.info(
                "[task] - Guild %s is not found, deleting role request %s",
                rr.guild_id,
                rr.id,
            )
            await self._delete_role_request(rr)
            return

        if not (
            channel := await ensure_messageable_channel_exists(
                guild, rr.channel_id
            )
        ):
            logger.info(
                "[task] - Role request channel %s not found in guild %s, "
                "deleting role request %s",
                rr.channel_id,
                rr.guild_id,
                rr.id,
            )
            await self._delete_role_request(rr)
            return

        if not (
            rr_message := await ensure_message_exists(
                self.bot, channel, rr.message_id
            )
        ):
            logger.info(
                "[task] - Role request message %s not found in guild %s, "
                "deleting role request %s from DB",
                rr.message_id,
                rr.guild_id,
                rr.id,
            )
            await self._delete_role_request(rr)
            return

        try:
            await self._delete_role_request(rr)

            logger.info(
                "[task] - Deleted role request %s in guild %s",
                rr.id,
                rr.guild_id,
            )

        except Exception as e:
            logger.error(
                "[task] - Failed to delete role request %s in guild %s: %s",
                rr.id,
                rr.guild_id,
                e,
            )
            return

        # Create RR view (default and state) and send them to check_rr_channel
        try:
            view = CheckRoleRequestView(
                self.bot,
                interaction_user_id=rr.author_id,
                interaction_user_nick="Unknown",
                role_requested_id=rr.role_id,
                moderator_id=None,
                state=RoleRequestStateEnum.EXPIRED,
                all_disabled=True,
            )

        except Exception as e:
            logger.error("Failed to create CheckRoleRequestView: %s", e)
            return

        try:
            updated_view = await rr_message.edit(view=view)

            asyncio.create_task(
                updated_view.reply(
                    view=RoleRequestStateView(
                        self.bot,
                        moderator_id=rr.moderator_id,
                        user_id=rr.author_id,
                        roles_ids=[rr.role_id],
                        state=RoleRequestStateEnum.EXPIRED,
                    )
                )
            )
        except Exception as e:
            logger.error(
                "Failed to edit role request message for user %s "
                "in guild %s: %s",
                rr.author_id,
                guild.id,
                e,
            )
            return

    async def _delete_role_request(self, rr: RoleRequestState) -> None:
        """Delete a role request from the database."""
        async with self.bot.uow.start() as session:
            _rr = await session.merge(rr)
            await session.delete(_rr)

    @delete_role_request_task.before_loop
    async def before_delete_role_request_task(self):
        """Prepare before starting the delete role request task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @delete_role_request_task.error
    async def delete_role_request_task_error(self, exc: BaseException) -> None:
        """Handle errors in the delete role request task."""
        logger.exception(
            "[task] - Delete role request task crashed:",
            exc_info=exc,
        )

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.delete_role_request_task.is_running():
            logger.info("[task] - Restarting delete role request task...")
            self.delete_role_request_task.restart()


async def setup(bot: "Nightcore"):
    """Setup the DeleteRoleRequestTask cog."""
    await bot.add_cog(DeleteRoleRequestTask(bot))
