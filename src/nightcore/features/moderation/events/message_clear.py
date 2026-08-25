"""MessageClear Event Cog for Nightcore Bot."""

import logging

from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.operations import (
    get_specified_webhook,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events import MessageClearEventData
from src.nightcore.features.moderation.utils.punish_notify import (
    send_moderation_log,
)
from src.utils._enums import ChannelType

logger = logging.getLogger(__name__)


class MessageClearEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_message_clear(
        self,
        *,
        data: MessageClearEventData,
    ) -> None:
        """Handle message clear events."""
        logger.info(
            "[event] on_message_clear - %s: Guild: %s, Member: %s, Channel: %s, Amount: %s",  # noqa: E501
            data.category,
            data.moderator.guild.id,
            data.moderator.id,
            data.channel_cleared_id,
            data.amount,
        )

        # getting logging channel
        async with self.bot.uow.start() as session:
            logging_webhook = await get_specified_webhook(
                session,
                guild_id=data.moderator.guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_MODERATION,
            )

        # sending log message
        if logging_webhook and logging_webhook.valid:
            await send_moderation_log(
                self.bot, webhook=logging_webhook, event_data=data
            )
        else:
            logger.info(
                "[event] on_message_clear - %s: Guild: %s, logging channel is not set",  # noqa: E501
                data.moderator.guild.id,
                data.category,
            )
            return


async def setup(bot: Nightcore):
    """Setup the MessageClearEvent cog."""
    await bot.add_cog(MessageClearEvent(bot))
