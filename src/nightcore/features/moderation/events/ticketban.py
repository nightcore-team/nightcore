"""Mute Events Cog for Nightcore Bot."""

import asyncio
import logging
from collections.abc import Awaitable
from datetime import timezone

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    create_punish,
    create_temp_punish,
    get_latest_temp_punish,
    get_specified_channel,
    set_user_field_upsert,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.events import (
    UnPunishEventData,
    UserMutedEventData,
)
from src.nightcore.features.moderation.utils import (
    send_moderation_log,
    send_punish_dm_message,
    send_unpunish_dm_message,
)
from src.nightcore.utils import discord_ts, get_discord_user
from src.nightcore.utils.time_utils import calculate_end_time

logger = logging.getLogger(__name__)


class UserTicketbannedEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_user_ticketbanned(
        self,
        *,
        data: UserMutedEventData,
    ) -> None:
        """Handle user punished events."""
        logger.info(
            "[event] on_user_muted - %s: Guild: %s, Member: %s, Reason: %s, Duration: %s",  # noqa: E501
            data.category,
            data.moderator.guild.id,
            data.user.id,
            data.reason,
            data.duration,
        )

        user = await get_discord_user(self.bot, data.user.id)
        if not user:
            logger.warning(
                "[event] on_user_ticketbanned - %s: Guild: %s, User: %s, User not found",  # noqa: E501
                data.category,
                data.moderator.guild.id,
                data.user.id,
            )
            return

        data.user = user

        end_time = calculate_end_time(data.duration)
        data.end_time = discord_ts(end_time)

        # db insert and getting logging channel
        async with self.bot.uow.start() as session:
            try:
                punish_info = await create_punish(
                    session,
                    guild_id=data.moderator.guild.id,
                    user_id=data.user.id,
                    moderator_id=data.moderator.id,
                    category=data.category,
                    reason=data.reason,
                    duration=data.duration,
                    end_time=end_time,
                    time_now=discord.utils.utcnow().astimezone(timezone.utc),
                )
            except Exception as e:
                logger.exception(
                    "[event] on_user_ticketbanned - %s: Failed to create punish record: %s",  # noqa: E501
                    data.category,
                    e,
                )
                return

            try:
                await create_temp_punish(
                    session,
                    guild_id=data.moderator.guild.id,
                    user_id=data.user.id,
                    category=data.category,
                    end_time=end_time,
                )
            except Exception as e:
                logger.exception(
                    "[event] on_user_ticketbanned - %s: Failed to create punish record: %s",  # noqa: E501
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

        gather_list.append(
            send_punish_dm_message(self.bot, event_data=data),
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
                "[event] on_user_ticketbanned - %s: Guild: %s, logging channel is not set",  # noqa: E501
                data.moderator.guild.id,
                punish_info.category,
            )

        try:
            await asyncio.gather(*gather_list, return_exceptions=True)
        except Exception as e:
            logger.exception(
                "[event] on_user_ticketbanned - %s: Failed to send DM or log message: %s",  # noqa: E501
                data.category,
                e,
            )

    @Cog.listener()
    async def on_user_unticketbanned(
        self, *, data: UnPunishEventData, by_command: bool = False
    ) -> None:
        """Handle user unticketban events."""
        logger.info(
            "[event] on_user_unticketbanned - %s: Guild: %s, Member: %s, Reason: %s",  # noqa: E501
            data.category,
            data.guild_id,
            data.user_id,
            data.reason,
        )

        guild = self.bot.get_guild(data.guild_id)
        if guild is None:
            logger.error(
                "[event] user_unmute - %s: Guild %s not in cache",
                data.category,
                data.guild_id,
            )
            return

        user = await get_discord_user(self.bot, data.user_id)
        if not user:
            logger.warning(
                "[event] on_user_unticketbanned - %s: Guild: %s, User: %s, User not found",  # noqa: E501
                data.category,
                data.guild_id,
                data.user_id,
            )
            return

        async with self.bot.uow.start() as session:
            if by_command:
                await create_punish(
                    session,
                    guild_id=data.guild_id,
                    user_id=data.user_id,
                    moderator_id=data.moderator_id,
                    category=f"un{data.category}",
                    reason=data.reason,
                    end_time=None,
                    time_now=discord.utils.utcnow().astimezone(timezone.utc),
                )

                temp = await get_latest_temp_punish(
                    session,
                    guild_id=data.guild_id,
                    user_id=data.user_id,
                    category=data.category,
                )
                if temp:
                    await session.delete(temp)

                else:
                    logger.error(
                        "[event] on_user_unticketbanned - %s: No active temporary punishment found for user %s in guild %s",  # noqa: E501
                        data.category,
                        data.user_id,
                        data.guild_id,
                    )

            try:
                await set_user_field_upsert(
                    session,
                    guild_id=guild.id,
                    user_id=user.id,
                    field="ticket_ban",
                    value=False,
                )
            except Exception as e:
                logger.exception(
                    "Failed to unticketban user=%s in guild=%s: %s",
                    user.id,
                    guild.id,
                    e,
                )
                return

            logging_channel_id = await get_specified_channel(
                session,
                guild_id=data.guild_id,
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

        gather_list.append(
            send_unpunish_dm_message(
                self.bot,
                user=user,
                category=data.category,
                guild_name=guild.name,
            )
        )

        try:
            await asyncio.gather(*gather_list, return_exceptions=True)
        except Exception as e:
            logger.exception(
                "[event] on_user_unticketbanned - %s: Failed to send DM or log message: %s",  # noqa: E501
                data.category,
                e,
            )


async def setup(bot: Nightcore):
    """Setup the UserTicketbannedEvent cog."""
    await bot.add_cog(UserTicketbannedEvent(bot))
