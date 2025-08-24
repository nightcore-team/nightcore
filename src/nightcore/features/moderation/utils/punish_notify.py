"""Utilities for sending punishment notifications."""

import logging
from datetime import datetime

import discord
from discord import Member, User

from src.infra.db.models.punish import Punish
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.components import (
    generate_dm_punish_embed,
    generate_log_punish_embed,
)

logger = logging.getLogger(__name__)


async def send_punish_dm_message(
    bot: Nightcore,
    *,
    moderator: Member,
    user: User,
    punish_type: str,
    reason: str,
    end_time: datetime | None = None,
) -> None:
    """Send a DM to the user about their punishment."""
    embed = generate_dm_punish_embed(
        punish_type=punish_type,
        guild_name=moderator.guild.name,
        moderator=moderator,
        reason=reason,
        end_time=end_time,
        bot=bot,
    )
    try:
        await user.send(embed=embed)
        logger.info(
            "[event] - on_user_punish - %s: DM sent to %s",
            punish_type,
            user.id,
        )
    except Exception as e:
        logger.exception(
            "[event] - on_user_punish - %s: Failed to send DM to %s: %s",
            punish_type,
            user.id,
            e,
        )


async def send_punish_log(
    bot: Nightcore,
    *,
    channel_id: int,
    duration: str | None = None,
    punish_info: Punish,
) -> None:
    """Send a punishment log message to the specified logging channel."""

    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            logger.warning(
                "[event] on_user_punish - %s: logging channel %s not found",
                punish_info.category,
                channel_id,
            )
            return
        except discord.Forbidden:
            logger.warning(
                "[event] on_user_punish - %s: no permission for channel %s",
                channel_id,
            )
            return
        except discord.HTTPException as e:
            logger.error(
                "[event] on_user_punish - %s: HTTP error fetching channel %s: %s",  # noqa: E501
                punish_info.category,
                channel_id,
                e,
            )
            return

    if isinstance(channel, discord.ForumChannel):
        logger.info(
            "[event] on_user_punish - %s: forum channel %s, creating thread",
            punish_info.category,
            channel.id,
        )
        try:
            await channel.create_thread(
                name=f"Punish ({punish_info.category}): {punish_info.user_id}",
                content=f"User punished: {punish_info.user_id}\nReason: {punish_info.reason}",  # noqa: E501
            )
        except discord.DiscordException as e:
            logger.error(
                "[event] on_user_punish - %s: failed to create forum thread in %s: %s",  # noqa: E501
                punish_info.category,
                channel.id,
                e,
            )
        return

    if not isinstance(channel, discord.TextChannel | discord.Thread):
        logger.warning(
            "[event] on_user_punish - %s: channel %s not messageable (%s)",
            punish_info.category,
            channel.id,
            type(channel).__name__,
        )
        return

    try:
        await channel.send(
            embed=generate_log_punish_embed(
                bot=bot,
                punish_type=punish_info.category,
                moderator_id=punish_info.moderator_id,
                user_id=punish_info.user_id,
                reason=punish_info.reason,
                duration=duration,
                end_time=punish_info.end_time,
            )
        )
    except discord.HTTPException as e:
        logger.error(
            "[event] on_user_punish - %s: failed to send message to %s: %s",
            punish_info.category,
            channel.id,
            e,
        )
