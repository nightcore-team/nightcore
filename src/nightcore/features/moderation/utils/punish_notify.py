"""Utilities for sending punishment notifications."""

import logging

import discord

from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.components import (
    generate_dm_punish_embed,
    generate_dm_un_punish_embed,
)
from src.nightcore.features.moderation.events import (
    RolesChangeEventData,
)
from src.nightcore.features.moderation.events.dto.base import (
    ModerationBaseEventData,
)

logger = logging.getLogger(__name__)


async def send_punish_dm_message(
    bot: Nightcore,
    *,
    event_data: ModerationBaseEventData,
) -> None:
    """Send a DM to the user about their punishment."""
    embed = generate_dm_punish_embed(
        punish_type=event_data.category,  # type: ignore
        guild_name=event_data.moderator.guild.name,  # type: ignore
        moderator=event_data.moderator,  # type: ignore
        reason=event_data.reason,  # type: ignore
        end_time=event_data.end_time,  # type: ignore
        bot=bot,
    )
    try:
        await event_data.user.send(embed=embed)  # type: ignore
        logger.info(
            "[event] - on_user_punish - %s: DM sent to %s",
            event_data.category,  # type: ignore
            event_data.user.id,  # type: ignore
        )
    except Exception as e:
        logger.exception(
            "[event] - on_user_punish - %s: Failed to send DM to %s: %s",
            event_data.category,  # type: ignore
            event_data.user.id,  # type: ignore
            e,
        )


async def send_unpunish_dm_message(
    bot: Nightcore,
    *,
    user: discord.Member | discord.User,
    category: str,
    guild_name: str,
) -> None:
    """Send a DM to the user about their unpunishment."""
    embed = generate_dm_un_punish_embed(
        punish_type=category,
        guild_name=guild_name,
        bot=bot,
    )
    try:
        await user.send(embed=embed)  # type: ignore
        logger.info(
            "[event] - on_user_unpunish - %s: DM sent to %s",
            category,
            user.id,
        )
    except Exception as e:
        logger.exception(
            "[event] - on_user_unpunish - %s: Failed to send DM to %s: %s",
            category,
            user.id,
            e,
        )


async def send_moderation_log(
    bot: Nightcore,
    *,
    channel_id: int,
    event_data: ModerationBaseEventData,
) -> None:
    """Send a moderation log message to the specified channel."""
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            logger.warning(
                "[event] on_user_punish - %s: logging channel %s not found",
                event_data.category,  # type: ignore
                channel_id,
            )
            return
        except discord.Forbidden:
            logger.warning(
                "[event] on_user_punish - %s: no permission for channel %s",
                event_data.category,  # type: ignore
                channel_id,
            )
            return
        except discord.HTTPException as e:
            logger.error(
                "[event] on_user_punish - %s: HTTP error fetching channel %s: %s",  # noqa: E501
                event_data.category,  # type: ignore
                channel_id,
                e,
            )
            return

    if not isinstance(channel, (discord.TextChannel | discord.Thread)):
        logger.warning(
            "[event] on_user_punish - %s: channel %s not messageable (%s)",
            event_data.category,  # type: ignore
            channel.id,
            type(channel).__name__,
        )
        return

    try:
        embed = event_data.build_embed(bot)
        await channel.send(embed=embed)
    except discord.HTTPException as e:
        logger.error(
            "[event] on_user_punish - %s: failed to send message to %s: %s",
            event_data.category,  # type: ignore
            channel.id,
            e,
        )


async def send_rr_channel_log(
    bot: Nightcore, *, channel_id: int, event_data: RolesChangeEventData
) -> None:
    """Send a moderation log message to the role request channel."""
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            logger.warning(
                "[event] %s: role request channel %s not found",
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

    if not isinstance(channel, (discord.TextChannel | discord.Thread)):
        logger.warning(
            "[event] %s: channel %s not messageable (%s)",
            event_data.category,
            channel.id,
            type(channel).__name__,
        )
        return

    text = f"`[🚮 | ROLE REMOVE]`  Moderator <@{event_data.moderator.id}> removed <@{event_data.user.id}> role <@&{event_data.role.id}>"  # noqa: E501

    try:
        await channel.send(content=text)
    except discord.HTTPException as e:
        logger.error(
            "[event] %s: failed to send message to %s: %s",
            event_data.category,
            channel.id,
            e,
        )
