"""Utilities for role members command."""

from discord import Member

from src.config.config import config


def build_rolemembers_pages(
    members: list[Member],
    is_v2: bool = False,
) -> list[str]:
    """Build paginated description pages for role members."""
    pages: list[str] = []
    current = ""

    limit = config.bot.EMBED_DESCRIPTION_LIMIT

    if is_v2:
        limit = config.bot.VIEW_V2_DESCRIPTION_LIMIT

    for member in members:
        line = f" {member.mention}"

        if len(current) + len(line) >= limit:
            pages.append(current)
            current = ""

        current += line

    if current:
        pages.append(current)

    if not pages:
        pages = ["Нет участников с этой ролью."]

    return pages
