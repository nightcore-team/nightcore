"""Utilities for sending punishment notifications."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING

import discord
from discord import Object

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models.discord_webhook import DiscordWebhook
from src.nightcore.features.moderation.components.v2.view.punish import (
    PunishViewV2,
)
from src.nightcore.features.moderation.events import (
    RolesChangeEventData,
)
from src.nightcore.features.moderation.events.dto.ban import (
    UserBannedEventData,
)
from src.nightcore.features.moderation.events.dto.base import (
    ModerationBaseEventData,
)
from src.nightcore.features.role_requests.components.v2 import (
    RoleRequestStateView,
)
from src.nightcore.utils.webhook import send_to_webhook
from src.utils._enums import RoleRequestStateEnum

logger = logging.getLogger(__name__)

# Idempotency: dedup caches keyed by stable event identifiers.
# Must be called after DB commit - dedup prevents double sends if retried
# after commit succeeded but notification dedup was not yet recorded.
# (Retry safety: DB commit is source of truth, sends are after commit.)
_DM_SENT_LOCK = asyncio.Lock()
_WEBHOOK_SENT_LOCK = asyncio.Lock()
_DM_SENT_CACHE: dict[str, float] = {}
_WEBHOOK_SENT_CACHE: dict[str, float] = {}
_IDEMPOTENCY_TTL_SECONDS = 3600.0


def _prune_cache(
    cache: dict[str, float], ttl: float = _IDEMPOTENCY_TTL_SECONDS
) -> None:
    """Remove expired entries from idempotency cache."""

    now = time.monotonic()
    expired = [k for k, ts in cache.items() if now - ts > ttl]
    for k in expired:
        cache.pop(k, None)


def _dm_idempotency_key(
    guild_name: str, event_data: ModerationBaseEventData
) -> str:
    """Stable idempotency key for DM notifications."""

    user_id = getattr(getattr(event_data, "user", None), "id", "unknown")
    category = getattr(event_data, "category", "unknown")
    # Include guild_name and category to disambiguate; punishment events have
    # no single global ID, so we use a composite key. Caller ensures this is
    # only computed after DB commit, so duplicate events map to same key.
    return f"dm:{guild_name}:{category}:{user_id}"


def _unpunish_dm_key(
    guild_name: str, user_id: int, category: str, moderator_id: int
) -> str:
    return f"un_dm:{guild_name}:{category}:{user_id}:{moderator_id}"


def _webhook_idempotency_key(
    webhook: DiscordWebhook, event_data: ModerationBaseEventData
) -> str:
    webhook_id = getattr(webhook, "id", webhook.url)
    user_obj = getattr(event_data, "user", None)
    user_id = getattr(
        user_obj, "id", getattr(event_data, "user_id", "unknown")
    )
    category = getattr(event_data, "category", "unknown")
    guild_id = _extract_guild_id(event_data)
    return f"webhook:{webhook_id}:{guild_id}:{category}:{user_id}"


async def send_punish_dm_message(
    bot: Nightcore,
    *,
    guild_name: str,
    event_data: ModerationBaseEventData,
) -> None:
    """Send a DM to the user about their punishment.

    Must be called **after** DB commit. Idempotent: duplicate calls with same
    event_data are deduped via in-memory cache to avoid double DM on retry.
    """

    key = _dm_idempotency_key(guild_name, event_data)
    async with _DM_SENT_LOCK:
        _prune_cache(_DM_SENT_CACHE)
        if key in _DM_SENT_CACHE:
            logger.info(
                "[%s/event] - DM deduped for %s (idempotency key %s)",
                getattr(event_data, "category", "unknown"),
                getattr(getattr(event_data, "user", None), "id", "unknown"),
                key,
            )
            return
        _DM_SENT_CACHE[key] = time.monotonic()

    view = PunishViewV2(
        bot=bot,
        user_id=event_data.user.id,  # type: ignore
        punish_type=event_data.category,  # type: ignore
        moderator_id=event_data.moderator_id
        if isinstance(event_data, UserBannedEventData)
        else event_data.moderator.id,  # type: ignore
        reason=event_data.reason,  # type: ignore
        duration=getattr(event_data, "original_duration", None),  # type: ignore
        mode="dm",
        guild_name=guild_name,
    )
    try:  # type: ignore
        await event_data.user.send(view=view)  # type: ignore
        logger.info(
            "[%s/event] - on_user_punish - DM sent to %s",
            event_data.category,  # type: ignore
            event_data.user.id,  # type: ignore
        )
    except discord.Forbidden:
        logger.info(
            "[%s/event] Failed to send DM to user %s because he doesn't accept DM",  # noqa: E501
            event_data.category,  # type: ignore
            event_data.user.id,  # type: ignore
        )
    except Exception as e:
        logger.warning(
            "[%s/event] Failed to send DM to user %s: %e",
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
    user_id: int,
    category: str,
    guild_name: str,
) -> None:
    """Send a DM to the user about their unpunishment.

    Must be called after DB commit. Idempotent via in-memory cache.
    """

    key = _unpunish_dm_key(guild_name, user_id, category, moderator_id)
    async with _DM_SENT_LOCK:
        _prune_cache(_DM_SENT_CACHE)
        if key in _DM_SENT_CACHE:
            logger.info(
                "[un%s/event] - DM deduped for %s (key %s)",
                category,
                user_id,
                key,
            )
            return
        _DM_SENT_CACHE[key] = time.monotonic()

    view = PunishViewV2(
        bot=bot,
        user_id=user_id,
        punish_type=category,
        mode=mode,
        guild_name=guild_name,
        moderator_id=moderator_id,
        reason=reason,
        duration=None,
    )

    try:
        channel = await bot.create_dm(Object(user_id))

        await channel.send(view=view)
        logger.info(
            "[%s/event] - on_user_unpunish - DM sent to %s",
            category,
            user_id,
        )
    except discord.Forbidden:
        logger.info(
            "[un%s/event] Failed to send DM to user %s because he doesn't accept DM",  # noqa: E501
            category,
            user_id,
        )
    except Exception as e:
        logger.warning(
            "[un%s/event] Failed to send DM to user %s: %e",
            category,
            user_id,
            e,
        )


def _extract_guild_id(event_data: ModerationBaseEventData) -> int:
    guild_id = getattr(event_data, "guild_id", None)
    if guild_id is not None:
        return guild_id
    moderator = getattr(event_data, "moderator", None)
    if moderator is not None:
        return moderator.guild.id
    guild = getattr(event_data, "guild", None)
    if guild is not None:
        return guild.id
    return 0


async def send_moderation_log(
    bot: Nightcore,
    *,
    webhook: DiscordWebhook,
    event_data: ModerationBaseEventData,
    attachments: Sequence[discord.File] | None = None,
) -> None:
    """Send a moderation log message to the specified webhook.

    Must be called after DB commit. Idempotent: duplicate webhook sends are
    deduped to avoid double log entries on event retry.
    """

    key = _webhook_idempotency_key(webhook, event_data)
    async with _WEBHOOK_SENT_LOCK:
        _prune_cache(_WEBHOOK_SENT_CACHE)
        if key in _WEBHOOK_SENT_CACHE:
            logger.info(
                "[%s/event] - moderation log deduped for guild %s (key %s)",
                getattr(event_data, "category", "unknown"),
                _extract_guild_id(event_data),
                key,
            )
            return
        _WEBHOOK_SENT_CACHE[key] = time.monotonic()

    embed = event_data.build_embed(bot)

    await send_to_webhook(
        bot,
        webhook,
        embed,
        context=event_data.category,  # type: ignore
        guild_id=_extract_guild_id(event_data),
        files=attachments,
    )


async def send_rr_channel_log(
    bot: Nightcore, *, channel_id: int, event_data: RolesChangeEventData
) -> None:
    """Send a moderation log message to the role request channel.

    Must be called after DB commit. Idempotent per channel+event.
    """

    key = f"rr:{channel_id}:{event_data.category}:{event_data.user.id}"
    async with _WEBHOOK_SENT_LOCK:
        _prune_cache(_WEBHOOK_SENT_CACHE)
        if key in _WEBHOOK_SENT_CACHE:
            logger.info(
                "[event] %s: rr channel log deduped for %s (key %s)",
                event_data.category,
                channel_id,
                key,
            )
            return
        _WEBHOOK_SENT_CACHE[key] = time.monotonic()

    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.NotFound:
            logger.info(
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
        reason=event_data.reason,
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
