"""Kick Event Cog for Nightcore Bot."""

import asyncio
import logging
from collections.abc import Awaitable
from datetime import UTC

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    create_punish,
    get_specified_channel,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events import UserKickEventData
from src.nightcore.features.moderation.utils.punish_notify import (
    send_moderation_log,
    send_punish_dm_message,
)

logger = logging.getLogger(__name__)


class UserKickEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_user_kicked(
        self,
        *,
        data: UserKickEventData,
    ) -> None:
        """Handle user kicked events."""
        logger.info(
            "[event] on_user_kicked - %s: Guild: %s, Member: %s, Reason: %s",
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
                "[event] on_user_kicked - %s: Failed to fetch user %s: %s",
                data.category,
                data.user.id,
                e,
            )
            return

        # db insert and getting logging channel
        async with self.bot.uow.start() as session:
            try:
                await create_punish(
                    session,
                    guild_id=data.moderator.guild.id,
                    user_id=data.user.id,
                    moderator_id=data.moderator.id,
                    category=data.category,
                    reason=data.reason,
                    end_time=None,
                    time_now=discord.utils.utcnow().astimezone(UTC),
                )
            except Exception as e:
                logger.exception(
                    "[event] on_user_kicked - %s: Failed to create punish record: %s",  # noqa: E501
                    data.category,
                    e,
                )
                return

            logging_channel_id = await get_specified_channel(
                session,
                guild_id=data.moderator.guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_MODERATION,
            )

        gather_list: list[Awaitable[None]] = []

        # send dm message to user
        gather_list.append(
            send_punish_dm_message(
                self.bot, guild_name=data.guild_name, event_data=data
            ),
        )

        # sending log message
        if logging_channel_id:
            gather_list.append(
                send_moderation_log(
                    self.bot, channel_id=logging_channel_id, event_data=data
                )
            )
        else:
            logger.warning(
                "[event] on_user_kicked - %s: Guild: %s, logging channel is not set",  # noqa: E501
                data.category,
                data.moderator.guild.id,
            )

        try:
            await asyncio.gather(*gather_list, return_exceptions=True)
        except Exception as e:
            logger.exception(
                "[event] on_user_kicked - %s: Failed to send DM or log message: %s",  # noqa: E501
                data.category,
                e,
            )


async def setup(bot: Nightcore):
    """Setup the UserKickEvent cog."""
    await bot.add_cog(UserKickEvent(bot))
