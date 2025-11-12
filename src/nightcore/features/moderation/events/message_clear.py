"""MessageClear Event Cog for Nightcore Bot."""

import asyncio
import logging
from collections.abc import Awaitable

from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    get_specified_channel,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events import MessageClearEventData
from src.nightcore.features.moderation.utils.punish_notify import (
    send_moderation_log,
)

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
            logging_channel_id = await get_specified_channel(
                session,
                guild_id=data.moderator.guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_MODERATION,
            )

        gather_list: list[Awaitable[None]] = []

        # sending log message
        if logging_channel_id:
            gather_list.append(
                send_moderation_log(
                    self.bot, channel_id=logging_channel_id, event_data=data
                )
            )
        else:
            logger.warning(
                "[event] on_message_clear - %s: Guild: %s, logging channel is not set",  # noqa: E501
                data.moderator.guild.id,
                data.category,
            )
            return

        try:
            await asyncio.gather(*gather_list, return_exceptions=True)
        except Exception as e:
            logger.exception(
                "[event] on_message_clear - %s: Guild: %s, Failed to send log message: %s",  # noqa: E501
                data.category,
                data.moderator.guild.id,
                e,
            )
            return


async def setup(bot: Nightcore):
    """Setup the MessageClearEvent cog."""
    await bot.add_cog(MessageClearEvent(bot))
