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
from src.nightcore.features.moderation.utils import (
    calculate_end_time,
    send_punish_dm_message,
    send_punish_log,
)

logger = logging.getLogger(__name__)


class ModerationEvents(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_un_user_punish(self):
        """Handle user unpunished events."""

    @Cog.listener()
    async def on_user_punish(
        self,
        *,
        moderator: discord.Member,
        member: discord.Member,
        category: str,
        duration: str | None = None,
        reason: str,
    ) -> None:
        """Handle user punished events."""
        logger.info(
            "[event] on_user_punish - %s: Guild: %s, Member: %s, Reason: %s",
            category,
            moderator.guild.id,
            member.id,
            reason,
        )

        try:
            user = await self.bot.fetch_user(member.id)
        except Exception as e:
            logger.exception(
                "[event] on_user_punish - %s: Failed to fetch user %s: %s",
                category,
                member.id,
                e,
            )
            return

        end_time = None
        if duration:
            end_time = calculate_end_time(duration)

        # db insert and getting logging channel
        async with self.bot.uow.start() as uow:
            try:
                punish_info = await create_punish(
                    session=cast(AsyncSession, uow.session),
                    guild_id=moderator.guild.id,
                    user_id=user.id,
                    moderator_id=moderator.id,
                    category=category,
                    reason=reason,
                    end_time=end_time,
                    time_now=discord.utils.utcnow(),
                )
            except Exception as e:
                logger.exception(
                    "[event] on_user_punish - %s: Failed to create punish record: %s",  # noqa: E501
                    category,
                    e,
                )
                return

            logging_channel_id = await get_specified_channel(
                cast(AsyncSession, uow.session),
                guild_id=moderator.guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_MODERATION,
            )

        # send dm message to user
        await send_punish_dm_message(
            self.bot,
            moderator=moderator,
            user=user,
            punish_type=category,
            reason=reason,
            end_time=end_time,
        )

        # sending log message
        if not logging_channel_id:
            logger.warning(
                "[event] on_user_punish - %s: Guild: %s, logging channel is not set",  # noqa: E501
                moderator.guild.id,
                punish_info.category,
            )
            return

        await send_punish_log(
            self.bot,
            channel_id=logging_channel_id,
            duration=duration,
            punish_info=punish_info,
        )


async def setup(bot: Nightcore):
    """Setup the ModerationEvents cog."""
    await bot.add_cog(ModerationEvents(bot))
