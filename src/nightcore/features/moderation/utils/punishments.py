"""Utilities for building paginated punishment descriptions."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from src.config.config import config

if TYPE_CHECKING:
    from src.infra.db.models import (
        Punish,
    )

from src.nightcore.utils import discord_ts

logger = logging.getLogger(__name__)

PUNISHMENTS_DESC_DICT: dict[str, dict[str, str]] = {
    "server": {
        "mute": "получил мут.",
        "unmute": "был разблокирован в чате.",
        "mpmute": "получил блокировку торговой площадки.",
        "unmpmute": "был разблокирован на торговой площадке.",
        "vmute": "получил блокировку голосового чата.",
        "unvmute": "был разблокирован в голосовом чате.",
        "kick": "был кикнут с сервера.",
        "ban": "был заблокирован на сервере.",
        "unban": "был разблокирован на сервере.",
        "rrban": "получил блокировку на запрос организационных ролей.",
        "unrrban": "был разблокирован на запрос организационных ролей.",
        "ticketban": "получил блокировку на создание тикетов.",
        "unticketban": "был разблокирован на создание тикетов.",
    },
    "dm": {
        "mute": "получили мут.",
        "unmute": "были разблокированы в чате.",
        "mpmute": "получили блокировку торговой площадки.",
        "unmpmute": "были разблокированы на торговой площадке.",
        "vmute": "получили блокировку голосового чата.",
        "unvmute": "были разблокированы в голосовом чате.",
        "kick": "были кикнуты с сервера.",
        "ban": "были заблокированы на сервере.",
        "unban": "были разблокированы на сервере.",
        "rrban": "получили блокировку на запрос организационных ролей.",
        "unrrban": "были разблокированы на запрос организационных ролей.",
        "ticketban": "получили блокировку на создание тикетов.",
        "unticketban": "были разблокированы в создании тикетов.",
    },
}


def build_infraction_pages(
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

        if p.original_duration:
            line += f"| {p.original_duration} "

        if p.reason:
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
