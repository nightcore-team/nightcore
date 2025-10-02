"""Utilities for building paginated punishment descriptions."""

import logging
from collections.abc import Sequence
from typing import TypedDict

from src.config.config import config
from src.infra.db.models import Punish, RoleRequestState, TicketState
from src.nightcore.utils import discord_ts

logger = logging.getLogger(__name__)


class ModeratorData(TypedDict):
    punishments: list[Punish]
    tickets: list[TicketState]
    role_requests: list[RoleRequestState]
    nickname: str


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


def build_moderators_stats(
    infractions: dict[int, ModeratorData],
    mute_score: float,
    ban_score: float,
    kick_score: float,
    vmute_score: float,
    mpmute_score: float,
    ticketban_score: float,
    tickets_score: float,
    approved_role_requests_score: float,
    changed_roles_score: float,
    message_score: float,
    total_messages: int,
) -> dict[int, dict[str, str]]:
    """Build a summary of moderation stats for each moderator."""
    stats: dict[int, dict[str, str]] = {}

    for moderator_id, data in infractions.items():
        punishes = data.get("punishments", [])
        _name = data.get("nickname", "")
        tickets = data.get("tickets", [])
        role_requests = data.get("role_requests", [])
        mute_count = sum(1 for p in punishes if p.category == "mute")
        ban_count = sum(1 for p in punishes if p.category == "ban")
        kick_count = sum(1 for p in punishes if p.category == "kick")
        vmute_count = sum(1 for p in punishes if p.category == "vmute")
        mpmute_count = sum(1 for p in punishes if p.category == "mpmute")
        ticketban_count = sum(1 for p in punishes if p.category == "ticketban")
        closed_tickets_count = len(tickets)
        approved_role_requests_count = len(role_requests)
        changed_roles_count = sum(
            1 for p in punishes if p.category == "role_remove"
        )
        total_points = (
            mute_count * mute_score
            + ban_count * ban_score
            + kick_count * kick_score
            + vmute_count * vmute_score
            + mpmute_count * mpmute_score
            + ticketban_count * ticketban_score
            # + closed_tickets_count * tickets_score
            # + approved_role_requests_count * approved_role_requests_score
            + changed_roles_count * changed_roles_score
            + total_messages * message_score
        )

        stats[moderator_id] = {}
        stats[moderator_id]["stats"] = (
            f"Mute: {mute_count}\n"
            f"Ban: {ban_count}\n"
            f"Kick: {kick_count}\n"
            f"Vmute: {vmute_count}\n"
            f"Mpmute: {mpmute_count}\n"
            f"Ticketban: {ticketban_count}\n"
            f"Closed tickets: {closed_tickets_count}\n"
            f"Approved role requests: {approved_role_requests_count}\n"
            f"Changed roles: {changed_roles_count}\n"
            f"Messages: {total_messages}\n\n"
            f"Total points: {total_points}"
        )
        stats[moderator_id]["nickname"] = _name

    return stats


def build_moderstats_pages(
    stats: dict[int, dict[str, str]],
) -> list[list[dict[int, dict[str, str]]]]:
    """Build paginated description pages for moderator stats."""
    pages: list[list[dict[int, dict[str, str]]]] = []

    current: list[dict[int, dict[str, str]]] = []

    for moderator_id, stat in stats.items():
        current.append({moderator_id: stat})

        if len(current) >= 6:
            pages.append(current)
            current = []

    if current:
        pages.append(current)

    return pages
