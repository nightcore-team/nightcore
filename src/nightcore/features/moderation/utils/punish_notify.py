"""Utilities for sending punishment notifications."""

import logging

import discord

from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.components import (
    generate_dm_punish_embed,
    generate_log_punish_embed,
)
from src.nightcore.features.moderation.utils.event_data import EventData

logger = logging.getLogger(__name__)


async def send_punish_dm_message(
    bot: Nightcore,
    *,
    event_data: EventData,
) -> None:
    """Send a DM to the user about their punishment."""
    embed = generate_dm_punish_embed(
        punish_type=event_data.category,
        guild_name=event_data.moderator.guild.name,
        moderator=event_data.moderator,
        reason=event_data.reason,
        end_time=event_data.end_time,
        bot=bot,
    )
    try:
        await event_data.member.send(embed=embed)
        logger.info(
            "[event] - on_user_punish - %s: DM sent to %s",
            event_data.category,
            event_data.member.id,
        )
    except Exception as e:
        logger.exception(
            "[event] - on_user_punish - %s: Failed to send DM to %s: %s",
            event_data.category,
            event_data.member.id,
            e,
        )


async def send_punish_log(
    bot: Nightcore,
    *,
    channel_id: int,
    event_data: EventData,
) -> None:
    """Send a punishment log message to the specified logging channel."""

    channel = bot.get_channel(channel_id)

    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            logger.warning(
                "[event] on_user_punish - %s: logging channel %s not found",
                event_data.category,
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
                event_data.category,
                channel_id,
                e,
            )
            return

    if isinstance(channel, discord.ForumChannel):
        logger.info(
            "[event] on_user_punish - %s: forum channel %s, creating thread",
            event_data.category,
            channel.id,
        )
        try:
            await channel.create_thread(
                name=f"Punish ({event_data.category}): {event_data.member.id}",
                embed=generate_log_punish_embed(
                    bot=bot,
                    punish_type=event_data.category,
                    moderator_id=event_data.moderator.id,
                    user_id=event_data.member.id,
                    reason=event_data.reason,
                    duration=event_data.duration,
                    end_time=event_data.end_time,
                ),
            )
        except discord.DiscordException as e:
            logger.error(
                "[event] on_user_punish - %s: failed to create forum thread in %s: %s",  # noqa: E501
                event_data.category,
                channel.id,
                e,
            )
        return

    if not isinstance(channel, discord.TextChannel | discord.Thread):
        logger.warning(
            "[event] on_user_punish - %s: channel %s not messageable (%s)",
            event_data.category,
            channel.id,
            type(channel).__name__,
        )
        return

    try:
        await channel.send(
            embed=generate_log_punish_embed(
                bot=bot,
                punish_type=event_data.category,
                moderator_id=event_data.moderator.id,
                user_id=event_data.member.id,
                reason=event_data.reason,
                duration=event_data.duration,
                end_time=event_data.end_time,
                old_nickname=event_data.old_nickname,
                new_nickname=event_data.new_nickname,
            )
        )
    except discord.HTTPException as e:
        logger.error(
            "[event] on_user_punish - %s: failed to send message to %s: %s",
            event_data.category,
            channel.id,
            e,
        )
