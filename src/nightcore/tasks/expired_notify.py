"""Task cog for handling expired notifications."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildNotificationsConfig
from src.infra.db.operations import (
    get_all_pending_notifications,
    get_specified_channel,
    get_specified_webhook,
)
from src.utils._enums import ChannelType, NotifyStateEnum

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.infra.db.models import NotifyState
    from src.nightcore.bot import Nightcore

from src.nightcore.features.moderation.components.v2.view import (
    NotifyTimedOutViewV2,
    NotifyViewV2,
)
from src.nightcore.utils import (
    ensure_guild_exists,
    ensure_message_exists,
    ensure_messageable_channel_exists,
)
from src.nightcore.utils.webhook import send_to_webhook

logger = logging.getLogger(__name__)

MAX_CONCURRENT_PROCESSING = 5


class ExpiredNotifyTask(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot
        self._processing_semaphore = asyncio.Semaphore(
            MAX_CONCURRENT_PROCESSING
        )

        self.expired_notify_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.expired_notify_task.is_running():
            self.expired_notify_task.cancel()

    @tasks.loop(seconds=15)
    async def expired_notify_task(self):
        """Task to handle expired notifications."""
        await self.bot.task_manager.sleep(__name__)

        try:
            logger.info("[task] - Running expired notify task")

            async with self.bot.uow.start() as session:
                pending_notifications = await get_all_pending_notifications(
                    session, now=datetime.now(UTC)
                )

            if not pending_notifications:
                logger.info("[task] - No pending notifications found")
                return

            processed = await self._process_notifications(
                pending_notifications
            )
            logger.info(
                "[task] - Completed expired notify task: processed=%s",
                processed,
            )

        except Exception as e:
            logger.exception(
                "[task] - Error in expired notify task iteration: %s",
                e,
                exc_info=True,
            )

    async def _process_notifications(
        self, notifications: Sequence[NotifyState]
    ) -> int:
        """Process notifications with rate limiting."""
        tasks: list[asyncio.Task[bool]] = []
        for notify in notifications:
            tasks.append(
                asyncio.create_task(self._process_single_with_limit(notify))
            )

        if not tasks:
            return 0

        results: list[bool | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        processed = 0
        for result in results:
            if result is True:
                processed += 1
            elif isinstance(result, Exception):
                logger.exception(
                    "[task] - Unexpected error processing notification"
                )

        return processed

    async def _process_single_with_limit(self, notify: NotifyState) -> bool:
        """Process a single notification with semaphore limiting."""
        async with self._processing_semaphore:
            try:
                await self._process_single(notify)
                return True
            except Exception:
                return False

    async def _process_single(self, notify: NotifyState) -> None:
        """Process a single notification."""

        guild = await ensure_guild_exists(self.bot, notify.guild_id)
        if guild is None:
            logger.info(
                "[task] - Guild %s not found, deleting notification",
                notify.guild_id,
            )
            await self._delete_notification(notify)
            return

        async with self.bot.uow.start() as session:
            moderation_notifications_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildNotificationsConfig,
                channel_type=ChannelType.MODERATION_NOTIFICATIONS,
            )
            notifications_config = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildNotificationsConfig,
                channel_type=ChannelType.NOTIFICATIONS,
            )

        if (
            not moderation_notifications_webhook
            or not moderation_notifications_webhook.valid
        ):
            logger.info(
                "[task] - Moderation notifications webhook not set in "
                "guild %s, deleting notification",
                guild.id,
            )
            await self._delete_notification(notify)
            return

        if not notifications_config:
            logger.info(
                "[task] - Notifications channel not set in guild %s, "
                "deleting notification",
                guild.id,
            )
            await self._delete_notification(notify)
            return

        if not (
            notifications_channel := await ensure_messageable_channel_exists(
                guild, notifications_config
            )
        ):
            logger.info(
                "[task] - Notifications channel %s not found in guild %s, "
                "deleting notification",
                notifications_config,
                guild.id,
            )
            await self._delete_notification(notify)
            return

        notification_message = await ensure_message_exists(
            self.bot, notifications_channel, notify.message_id
        )

        if not notification_message:
            logger.info(
                "[task] - Notification message %s not found in guild %s, "
                "deleting notification",
                notify.message_id,
                guild.id,
            )
            await self._delete_notification(notify)
            return

        view = NotifyViewV2(self.bot)
        view.guild_id = guild.id
        view.rebuild_component(notification_message.components, disabled=True)

        try:
            await notification_message.edit(view=view)
        except Exception as e:
            logger.error(
                "[task] - Failed to edit notification message %s "
                "in guild %s: %s",
                notification_message.id,
                guild.id,
                e,
            )

        await send_to_webhook(
            self.bot,
            moderation_notifications_webhook,
            NotifyTimedOutViewV2(
                self.bot,
                notify.moderator_id,
                notification_message.jump_url,
            ),
            context="expired_notify",
            guild_id=guild.id,
        )

        try:
            async with self.bot.uow.start() as session:
                _notify = await session.merge(notify)
                _notify.state = NotifyStateEnum.TIMED_OUT
        except Exception as e:
            logger.error(
                "[task] - Failed to update notification %s "
                "state in guild %s: %s",
                notify.id,
                guild.id,
                e,
            )
            return

        logger.info(
            "[task] - Notification for user %s in guild %s timed out",
            notify.user_id,
            guild.id,
        )

    async def _delete_notification(self, notify: NotifyState) -> None:
        """Delete a notification from the database."""
        async with self.bot.uow.start() as session:
            _notify = await session.merge(notify)
            await session.delete(_notify)

    @expired_notify_task.before_loop
    async def before_expired_notify_task(self):
        """Prepare before starting the expired notify task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @expired_notify_task.error
    async def expired_notify_task_error(self, exc: BaseException) -> None:
        """Handle errors in the expired notify task."""
        logger.exception("[task] - Expired notify task crashed:", exc_info=exc)

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.expired_notify_task.is_running():
            logger.info("[task] - Restarting expired notify task...")
            self.expired_notify_task.restart()


async def setup(bot: Nightcore):
    """Setup the ExpiredNotifyTask cog."""
    await bot.add_cog(ExpiredNotifyTask(bot))
