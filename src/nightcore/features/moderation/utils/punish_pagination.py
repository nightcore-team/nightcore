"""Utilities for building paginated punishment descriptions."""

import logging
from collections.abc import Sequence

from src.config.config import config
from src.infra.db.models.punish import Punish
from src.nightcore.utils import discord_ts

logger = logging.getLogger(__name__)


def build_pages(
    punishments: Sequence[Punish],
    guild_id: int,
    notify_channel_id: int | None = None,
    is_v2: bool = False,
) -> list[str]:
    """Build paginated description pages for infractions."""
    pages: list[str] = []
    current = ""

    limit = config.bot.EMBED_DESCRIPTION_LIMIT

    if is_v2:
        limit = config.bot.VIEW_V2_DESCRIPTION_LIMIT

    for p in punishments:
        line = f"**`[{p.category.upper()}]` | {discord_ts(p.time_now, style='d')} "  # noqa: E501

        if p.duration:
            line += f"| {p.duration} "

        if p.reason:
            if p.category == "notify" and notify_channel_id:
                line += f"| [notify](https://discord.com/channels/{guild_id}/{notify_channel_id})"
            else:
                line += f"| {p.reason} "
        line += f"||**<@{p.moderator_id}>\n"

        if len(current) + len(line) >= limit:
            pages.append(current)
            current = ""

        current += line

    if current:
        pages.append(current)

    if not pages:
        pages = ["No infractions."]

    return pages
