"""Utilities for sending punishment notifications."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models._enums import RoleRequestStateEnum
from src.nightcore.features.moderation.components.v2 import PunishViewV2
from src.nightcore.features.moderation.events import (
    RolesChangeEventData,
)
from src.nightcore.features.moderation.events.dto.base import (
    ModerationBaseEventData,
)
from src.nightcore.features.role_requests.components.v2 import (
    RoleRequestStateView,
)

logger = logging.getLogger(__name__)


async def send_punish_dm_message(
    bot: Nightcore,
    *,
    guild_name: str,
    event_data: ModerationBaseEventData,
) -> None:
    """Send a DM to the user about their punishment."""

    view = PunishViewV2(
        bot=bot,
        user=event_data.user,  # type: ignore
        punish_type=event_data.category,  # type: ignore
        moderator_id=event_data.moderator.id,  # type: ignore
        reason=event_data.reason,  # type: ignore
        duration=getattr(event_data, "original_duration", None),  # type: ignore
        mode="dm",
        guild_name=guild_name,
    )
    try:  # type: ignore
        await event_data.user.send(view=view)  # type: ignore
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
    mode: str,
    reason: str,
    moderator_id: int,
    user: discord.Member | discord.User,
    category: str,
    guild_name: str,
) -> None:
    """Send a DM to the user about their unpunishment."""

    view = PunishViewV2(
        bot=bot,
        user=user,
        punish_type=category,
        mode=mode,
        guild_name=guild_name,
        moderator_id=moderator_id,
        reason=reason,
        duration=None,
    )
    try:
        await user.send(view=view)  # type: ignore
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
    attachments: Sequence[discord.File] | None = None,
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
        if attachments:
            await channel.send(embed=embed, files=attachments)
        else:
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

    view = RoleRequestStateView(
        bot=bot,
        moderator_id=event_data.moderator.id,
        user_id=event_data.user.id,
        state=RoleRequestStateEnum.REMOVED,
        roles_ids=event_data.roles_ids,
    )

    try:
        await channel.send(view=view)
    except discord.HTTPException as e:
        logger.error(
            "[event] %s: failed to send message to %s: %s",
            event_data.category,
            channel.id,
            e,
        )
