"""Moderation Events Cog for Nightcore Bot."""

import logging
from typing import cast

import discord
from discord.ext.commands import Cog  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models._enums import LoggingChannelType
from src.infra.db.operations import (
    create_punish,
    get_specified_logging_channel,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.utils import send_punish_dm_message

logger = logging.getLogger(__name__)


class ModerationEvents(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_user_kicked(
        self,
        *,
        moderator: discord.Member,
        member: discord.Member,
        category: str,
        reason: str,
    ) -> None:
        """Handle user kicked events."""
        logger.info(
            "[event] user_kicked - User kicked: %s, Reason: %s",
            member,
            reason,
        )

        try:
            user = await self.bot.fetch_user(member.id)
        except Exception as e:
            logger.exception(
                "[event] user_kicked - Failed to fetch user %s: %s",
                member.id,
                e,
            )
            return

        # send dm message to user
        await send_punish_dm_message(
            self.bot,
            moderator,
            user,
            "kick",
            reason,
        )

        # db insert and getting logging channel
        async with self.bot.uow.start() as uow:
            await create_punish(
                session=cast(AsyncSession, uow.session),
                guild_id=moderator.guild.id,
                user_id=user.id,
                moderator_id=moderator.id,
                category=category,
                reason=reason,
                time_now=discord.utils.utcnow(),
            )

            logging_channel_id = await get_specified_logging_channel(
                cast(AsyncSession, uow.session),
                guild_id=moderator.guild.id,
                channel_type=LoggingChannelType.MODERATION,  # type: ignore
            )

        # if statements for checking logging channel availability and sending message #  noqa: E501
        if not logging_channel_id:
            logger.warning(
                "[event] user_kicked - logging channel is not set",
            )
            return

        channel = self.bot.get_channel(logging_channel_id)

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(logging_channel_id)
            except discord.NotFound:
                logger.warning(
                    "[event] user_kicked - logging channel %s not found",
                    logging_channel_id,
                )
                return
            except discord.Forbidden:
                logger.warning(
                    "[event] user_kicked - no permission for channel %s",
                    logging_channel_id,
                )
                return
            except discord.HTTPException as e:
                logger.error(
                    "[event] user_kicked - HTTP error fetching channel %s: %s",
                    logging_channel_id,
                    e,
                )
                return

        if isinstance(channel, discord.ForumChannel):
            logger.info(
                "[event] user_kicked - forum channel %s, creating thread",
                channel.id,
            )
            try:
                await channel.create_thread(
                    name=f"Kick: {member}",
                    content=f"User kicked: {member}\nReason: {reason}",
                )
            except discord.DiscordException as e:
                logger.error(
                    "[event] user_kicked - failed to create forum thread in %s: %s",  # noqa: E501
                    channel.id,
                    e,
                )
            return

        if not isinstance(channel, discord.TextChannel | discord.Thread):
            logger.warning(
                "[event] user_kicked - channel %s not messageable (%s)",
                channel.id,
                type(channel).__name__,
            )
            return

        try:
            await channel.send(
                f"User kicked: {member}, Reason: {reason}",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException as e:
            logger.error(
                "[event] user_kicked - failed to send message to %s: %s",
                channel.id,
                e,
            )


async def setup(bot: Nightcore):
    """Setup the ModerationEvents cog."""
    await bot.add_cog(ModerationEvents(bot))
