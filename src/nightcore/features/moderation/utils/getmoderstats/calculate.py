"""Utilities for calculating moderator statistics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._types import ModeratorStats

if TYPE_CHECKING:
    from src.infra.db.models._annot import ModerationInfractionsDataAnnot


def calculate_moderator_stats(
    moderator_id: int,
    data: ModerationInfractionsDataAnnot,
) -> ModeratorStats:
    """Рахує статистику з згрупованих даних."""

    punishment_counts: dict[str, int] = {}
    for punishment in data.punishments:
        category = punishment.category
        punishment_counts[category] = punishment_counts.get(category, 0) + 1

    deducted_points = sum(cs.amount for cs in data.changestats)

    return ModeratorStats(
        moderator_id=moderator_id,
        nickname=data.nickname,
        mute_count=punishment_counts.get("mute", 0),
        ban_count=punishment_counts.get("ban", 0),
        kick_count=punishment_counts.get("kick", 0),
        vmute_count=punishment_counts.get("vmute", 0),
        mpmute_count=punishment_counts.get("mpmute", 0),
        ticketban_count=punishment_counts.get("ticketban", 0),
        removed_roles_count=punishment_counts.get("role_remove", 0),
        closed_tickets_count=len(data.tickets),
        approved_role_requests_count=len(data.role_requests),
        deducted_points=deducted_points,
        changestat_details=list(data.changestats),
    )


def calculate_all_moderators_stats(
    grouped: dict[int, ModerationInfractionsDataAnnot],
) -> dict[int, ModeratorStats]:
    """Count stats for all moderators.

    Args:
        grouped: {moderator_id: ModerationInfractionsDataAnnot}

    Returns:
        {moderator_id: ModeratorStats}
    """
    return {
        moderator_id: calculate_moderator_stats(moderator_id, data)
        for moderator_id, data in grouped.items()
    }
