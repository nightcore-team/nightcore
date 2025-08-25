"""Utilities for building paginated punishment descriptions."""

from collections.abc import Sequence

from src.config.config import config
from src.infra.db.models.punish import Punish

from .time_utils import discord_ts


def build_pages(
    punishments: Sequence[Punish],
    guild_id: int,
    notify_channel_id: int | None = None,
) -> list[str]:
    """Build paginated description pages for infractions."""
    pages: list[str] = []
    current = ""

    for p in punishments:
        line = f"**`[{p.category.upper()}]` | {discord_ts(p.time_now, style='d')} "  # noqa: E501

        if p.duration:
            line += f"| {p.duration} "

        if p.reason:
            if p.category == "notify" and notify_channel_id:
                line += f"| [notify](https://discord.com/channels/{guild_id}/{notify_channel_id}"
            else:
                line += f"| {p.reason} "
        line += f"||**<@{p.moderator_id}>\n"

        if len(current) + len(line) > config.bot.EMBED_DESCRIPTION_LIMIT:
            pages.append(current)
            current = ""
        current += line

    if current:
        pages.append(current)

    if not pages:
        pages = ["No infractions."]

    return pages
