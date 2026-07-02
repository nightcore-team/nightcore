"""Utility functions for logging events."""

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

import discord

from src.infra.db.models.discord_webhook import DiscordWebhook

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.events.dto.base import BaseEventDTO

logger = logging.getLogger(__name__)


async def send_to_webhook(
    bot: "Nightcore",
    webhook_model: "DiscordWebhook",
    component: discord.Embed | discord.ui.LayoutView,
    *,
    context: str,
    guild_id: int,
    files: Sequence[discord.File] | None = None,
) -> bool:
    """Send a component to a Discord webhook, invalidating it on failure."""
    webhook = discord.Webhook.from_url(webhook_model.url, client=bot)
    try:
        if isinstance(component, discord.Embed):
            await webhook.send(embed=component, files=files or [])
        else:
            await webhook.send(view=component)
        return True
    except (discord.NotFound, discord.Forbidden):
        async with bot.uow.start() as session:
            merged = await session.merge(webhook_model, load=False)
            merged.valid = False
        return False
    except Exception as e:
        logger.error(
            "[%s/log] Failed to send message to webhook in guild %s: %s",
            context,
            guild_id,
            e,
        )
        return False


async def send_webhook_message(bot: "Nightcore", dto: "BaseEventDTO"):
    """Send a log message based on the provided DTO."""
    if not dto.logging_webhook:
        logger.info(
            "[%s/log] No logging channel configured for guild %s",
            dto.event_type,
            dto.guild.id,
        )
        return
    if not dto.logging_webhook.valid:
        logger.info(
            "[%s/log] Not valid webhook provided for logging in guild %s",
            dto.event_type,
            dto.guild.id,
        )
        return

    component = dto.build_component(bot)
    await send_to_webhook(
        bot,
        dto.logging_webhook,
        component,
        context=dto.event_type,
        guild_id=dto.guild.id,
    )
