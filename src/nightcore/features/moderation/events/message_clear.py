"""Moderation Events Cog for Nightcore Bot."""

import logging
from typing import cast

from discord.ext.commands import Cog  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    get_specified_channel,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events import MessageClearEventData
from src.nightcore.features.moderation.utils import (
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
        """Handle user punished events."""
        logger.info(
            "[event] on_user_punish - %s: Guild: %s, Member: %s, Channel: %s, Amount: %s",  # noqa: E501
            data.category,
            data.moderator.guild.id,
            data.channel_cleared_id,
            data.amount,
        )

        # getting logging channel
        async with self.bot.uow.start() as uow:
            logging_channel_id = await get_specified_channel(
                cast(AsyncSession, uow.session),
                guild_id=data.moderator.guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_MODERATION,
            )

        # sending log message
        if not logging_channel_id:
            logger.warning(
                "[event] on_user_punish - %s: Guild: %s, logging channel is not set",  # noqa: E501
                data.moderator.guild.id,
                data.category,
            )
            return

        try:
            await send_moderation_log(
                self.bot, channel_id=logging_channel_id, event_data=data
            )
        except Exception as e:
            logger.exception(
                "[event] on_user_punish - %s: Guild: %s, Failed to send log message: %s",  # noqa: E501
                data.category,
                data.moderator.guild.id,
                e,
            )


async def setup(bot: Nightcore):
    """Setup the MessageClearEvent cog."""
    await bot.add_cog(MessageClearEvent(bot))
