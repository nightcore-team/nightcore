"""SetName Event Cog for Nightcore Bot."""

import logging
from datetime import UTC

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.operations import (
    create_punish,
    get_specified_webhook,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events import UserSetNameEventData
from src.nightcore.features.moderation.utils.punish_notify import (
    send_moderation_log,
)
from src.utils._enums import ChannelType

logger = logging.getLogger(__name__)


class UserSetNameEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_user_setname(
        self,
        *,
        data: UserSetNameEventData,
    ) -> None:
        """Handle user setname events."""

        logger.info(
            "[event] on_user_setname - %s: Guild: %s, Member: %s, Reason: %s",
            data.category,
            data.moderator.guild.id,
            data.user.id,
            data.reason,
        )

        try:
            async with self.bot.uow.start() as session:
                punish_info = await create_punish(
                    session,
                    guild_id=data.moderator.guild.id,
                    user_id=data.user.id,
                    moderator_id=data.moderator.id,
                    category=data.category,
                    reason=data.reason,
                    end_time=None,
                    time_now=discord.utils.utcnow().astimezone(UTC),
                )

                logging_webhook = await get_specified_webhook(
                    session,
                    guild_id=data.moderator.guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_MODERATION,
                )

        except Exception as e:
            logger.exception(
                "[event] on_user_setname - %s: Failed to create punish record: %s",  # noqa: E501
                data.category,
                e,
            )
            return

        if logging_webhook and logging_webhook.valid:
            await send_moderation_log(
                self.bot, webhook=logging_webhook, event_data=data
            )
        else:
            logger.info(
                "[event] on_user_setname - %s: Guild: %s, logging channel is not set",  # noqa: E501
                data.moderator.guild.id,
                punish_info.category,
            )


async def setup(bot: Nightcore):
    """Setup the UserSetNameEvent cog."""
    await bot.add_cog(UserSetNameEvent(bot))
