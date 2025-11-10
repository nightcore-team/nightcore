"""Task cog for unpunishing users."""

import asyncio
import logging
from datetime import datetime, timezone

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildNotificationsConfig
from src.infra.db.models._enums import ChannelType, NotifyStateEnum
from src.infra.db.operations import (
    get_all_pending_notifications,
    get_specified_channel,
)
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

logger = logging.getLogger(__name__)


class ExpiredNotifyTask(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

        self.expired_notify_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.expired_notify_task.is_running():
            self.expired_notify_task.cancel()

    @tasks.loop(seconds=15)
    async def expired_notify_task(self):
        """Task to delete tickets when their duration ends."""
        logger.info("[task] - Running expired notify task")
        async with self.bot.uow.start() as session:
            pending_notifications = await get_all_pending_notifications(
                session
            )

            for notify in pending_notifications:
                if not notify.end_time < datetime.now(timezone.utc):
                    continue

                guild = await ensure_guild_exists(self.bot, notify.guild_id)
                if guild is None:
                    logger.error(
                        "[task] - Guild %s not found",
                        notify.guild_id,
                    )
                    continue

                moderation_notifications = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildNotificationsConfig,
                    channel_type=ChannelType.MODERATION_NOTIFICATIONS,
                )
                notifications = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildNotificationsConfig,
                    channel_type=ChannelType.NOTIFICATIONS,
                )
                if not moderation_notifications:
                    logger.error(
                        "[task] - Moderation notifications channel not set in guild %s",  # noqa: E501
                        guild.id,
                    )
                    continue

                if not notifications:
                    logger.error(
                        "[task] - Notifications channel not set in guild %s",
                        guild.id,
                    )
                    continue

                if not (
                    moderation_notifications_channel
                    := await ensure_messageable_channel_exists(
                        guild, moderation_notifications
                    )
                ):
                    logger.error(
                        "[task] - Moderation notifications channel %s not found in guild %s",  # noqa: E501
                        moderation_notifications,
                        guild.id,
                    )
                    continue

                if not (
                    notifications_channel
                    := await ensure_messageable_channel_exists(
                        guild, notifications
                    )
                ):
                    logger.error(
                        "[task] - Notifications channel %s not found in guild %s",  # noqa: E501
                        notifications,
                        guild.id,
                    )
                    continue

                notification_message = await ensure_message_exists(
                    self.bot, notifications_channel, notify.message_id
                )

                if not notification_message:
                    logger.error(
                        "[task] - Notification message %s not found in guild %s",  # noqa: E501
                        notify.message_id,
                        guild.id,
                    )
                    continue

                view = NotifyViewV2(self.bot)
                view.guild_id = guild.id
                view.rebuild_component(
                    notification_message.components, disabled=True
                )

                try:
                    await notification_message.edit(view=view)
                except Exception as e:
                    logger.error(
                        "[task] - Failed to edit notification message %s in guild %s: %s",  # noqa: E501
                        notification_message.id,
                        guild.id,
                        e,
                    )

                try:
                    asyncio.create_task(
                        moderation_notifications_channel.send(  # type: ignore
                            view=NotifyTimedOutViewV2(
                                self.bot,
                                notify.moderator_id,
                                notification_message.jump_url,
                            )
                        )
                    )
                except Exception as e:
                    logger.error(
                        "[task] - Failed to send moderation notification in guild %s: %s",  # noqa: E501
                        guild.id,
                        e,
                    )

                notify.state = NotifyStateEnum.TIMED_OUT

                logger.info(
                    "[task] - Notification for user %s in guild %s timed out",
                    notify.user_id,
                    guild.id,
                )

    @expired_notify_task.before_loop
    async def before_expired_notify_task(self):
        """Prepare before starting the expired notify task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @expired_notify_task.error
    async def expired_notify_task_error(self, exc):  # type: ignore
        """Handle errors in the expired notify task."""
        logger.exception("[task] - Expired notify task crashed:", exc_info=exc)  # type: ignore
        raise exc


async def setup(bot: Nightcore):
    """Setup the ExpiredNotifyTask cog."""
    await bot.add_cog(ExpiredNotifyTask(bot))
