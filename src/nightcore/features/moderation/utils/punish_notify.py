"""Utilities for sending punishment notifications."""

import logging

import discord

from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.components import (
    generate_dm_punish_embed,
)
from src.nightcore.features.moderation.events import (
    UserPunishmentEventData,
)
from src.nightcore.features.moderation.events.dto.base import (
    ModerationLogEventType,
)

logger = logging.getLogger(__name__)


async def send_punish_dm_message(
    bot: Nightcore,
    *,
    event_data: UserPunishmentEventData,
) -> None:
    """Send a DM to the user about their punishment."""
    embed = generate_dm_punish_embed(
        punish_type=event_data.category,
        guild_name=event_data.moderator.guild.name,
        moderator=event_data.moderator,
        reason=event_data.reason,  # type: ignore
        end_time=event_data.end_time,
        bot=bot,
    )
    try:
        await event_data.user.send(embed=embed)
        logger.info(
            "[event] - on_user_punish - %s: DM sent to %s",
            event_data.category,
            event_data.user.id,
        )
    except Exception as e:
        logger.exception(
            "[event] - on_user_punish - %s: Failed to send DM to %s: %s",
            event_data.category,
            event_data.user.id,
            e,
        )


async def send_moderation_log(
    bot: Nightcore,
    *,
    channel_id: int,
    event_data: ModerationLogEventType,
) -> None:
    """Send a moderation log message to the specified channel."""
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            logger.warning(
                "[event] %s: logging channel %s not found",
                event_data.category,
                channel_id,
            )
            return
        except discord.Forbidden:
            logger.warning(
                "[event] %s: no permission for channel %s",
                event_data.category,
                channel_id,
            )
            return
        except discord.HTTPException as e:
            logger.error(
                "[event] %s: HTTP error fetching channel %s: %s",
                event_data.category,
                channel_id,
                e,
            )
            return

    embed = event_data.build_embed(bot)

    if not isinstance(channel, (discord.TextChannel | discord.Thread)):
        logger.warning(
            "[event] %s: channel %s not messageable (%s)",
            event_data.category,
            channel.id,
            type(channel).__name__,
        )
        return

    try:
        await channel.send(embed=embed)
    except discord.HTTPException as e:
        logger.error(
            "[event] %s: failed to send message to %s: %s",
            event_data.category,
            channel.id,
            e,
        )
