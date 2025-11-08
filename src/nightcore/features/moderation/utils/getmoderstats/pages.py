"""Utilities to build moderator statistics pages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from discord.ui import Item, Separator, TextDisplay

if TYPE_CHECKING:
    from src.nightcore.features.moderation.utils.getmoderstats._types import (
        ModerationScores,
        ModeratorStats,
    )


def build_moderstats_pages(
    stats: dict[int, ModeratorStats],
    scores: ModerationScores,
    moderators_per_page: int = 3,
) -> list[list[tuple[int, ModeratorStats, float]]]:
    """Build paginated pages for moderator statistics.

    Returns:
        List of pages, each page contains list of (mod_id, stats, total_points)
    """
    results: list[tuple[int, ModeratorStats, float]] = []
    for mod_id, mod_stats in stats.items():
        total_points = mod_stats.calculate_total_points(scores)
        results.append((mod_id, mod_stats, total_points))

    results.sort(key=lambda x: x[2], reverse=True)

    pages: list[list[tuple[int, ModeratorStats, float]]] = []
    for i in range(0, len(results), moderators_per_page):
        page = results[i : i + moderators_per_page]
        pages.append(page)

    return pages if pages else [[]]


def format_moderstats_page_components(
    page: list[tuple[int, ModeratorStats, float]],
    page_number: int,
) -> list[Item[Any]]:
    """Format a single page of moderator statistics as components.

    Returns:
        List of TextDisplay and Separator components
    """
    if not page:
        return [TextDisplay("Нет данных для отображения.")]

    components: list[Item[Any]] = []
    start_rank = (page_number - 1) * len(page) + 1

    for idx, (mod_id, mod_stats, total_points) in enumerate(page):
        rank = start_rank + idx

        # Текст статистики модератора
        text = (
            f"### {rank}. {mod_stats.nickname} (<@{mod_id}>)\n"
            f"> **Муты:** {mod_stats.mute_count}\n"
            f"> **Баны:** {mod_stats.ban_count}\n"
            f"> **Кики:** {mod_stats.kick_count}\n"
            f"> **Войс муты:** {mod_stats.vmute_count}\n"
            f"> **MП муты:** {mod_stats.mpmute_count}\n"
            f"> **Тикет баны:** {mod_stats.ticketban_count}\n"
            f"> **Снятые роли:** {mod_stats.removed_roles_count}\n"
            f"> **Закрытые тикеты:** {mod_stats.closed_tickets_count}\n"
            f"> **Одобренные запросы ролей:** {mod_stats.approved_role_requests_count}\n"  # noqa: E501
            f"> **Количество баллов:** **`{total_points}`**\n"
            f"> **Количество снятых баллов:** {mod_stats.deducted_points}"
        )

        components.append(TextDisplay(text))

        if idx < len(page) - 1:
            components.append(Separator())

    return components
