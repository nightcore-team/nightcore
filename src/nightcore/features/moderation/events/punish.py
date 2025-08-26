"""Moderation Events Cog for Nightcore Bot."""

import logging
from typing import cast

import discord
from discord.ext.commands import Cog  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    create_punish,
    get_specified_channel,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events import UserPunishmentEventData
from src.nightcore.features.moderation.utils import (
    calculate_end_time,
    send_moderation_log,
    send_punish_dm_message,
)

logger = logging.getLogger(__name__)


class UserPunishEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_un_user_punish(self):
        """Handle user unpunished events."""

    @Cog.listener()
    async def on_user_punish(
        self,
        *,
        data: UserPunishmentEventData,
    ) -> None:
        """Handle user punished events."""
        logger.info(
            "[event] on_user_punish - %s: Guild: %s, Member: %s, Reason: %s",
            data.category,
            data.moderator.guild.id,
            data.user.id,
            data.reason,
        )

        try:
            user = await self.bot.fetch_user(data.user.id)
            data.user = user
        except Exception as e:
            logger.exception(
                "[event] on_user_punish - %s: Failed to fetch user %s: %s",
                data.category,
                data.user.id,
                e,
            )
            return

        end_time = None
        if data.duration:
            end_time = calculate_end_time(data.duration)
            data.end_time = end_time

        # db insert and getting logging channel
        async with self.bot.uow.start() as uow:
            try:
                punish_info = await create_punish(
                    session=cast(AsyncSession, uow.session),
                    guild_id=data.moderator.guild.id,
                    user_id=data.user.id,
                    moderator_id=data.moderator.id,
                    category=data.category,
                    reason=data.reason,  # type: ignore
                    end_time=end_time,
                    time_now=discord.utils.utcnow(),
                )
            except Exception as e:
                logger.exception(
                    "[event] on_user_punish - %s: Failed to create punish record: %s",  # noqa: E501
                    data.category,
                    e,
                )
                return

            logging_channel_id = await get_specified_channel(
                cast(AsyncSession, uow.session),
                guild_id=data.moderator.guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_MODERATION,
            )

        # send dm message to user
        if data.send_dm:
            await send_punish_dm_message(self.bot, event_data=data)

        # sending log message
        if not logging_channel_id:
            logger.warning(
                "[event] on_user_punish - %s: Guild: %s, logging channel is not set",  # noqa: E501
                data.moderator.guild.id,
                punish_info.category,
            )
            return

        await send_moderation_log(
            self.bot, channel_id=logging_channel_id, event_data=data
        )


async def setup(bot: Nightcore):
    """Setup the UserPunishEvent cog."""
    await bot.add_cog(UserPunishEvent(bot))
