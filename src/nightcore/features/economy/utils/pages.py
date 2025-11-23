"""Build transfers history pages."""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from src.config.config import config

if TYPE_CHECKING:
    from src.infra.db.models import TransferHistory

from src.nightcore.utils import discord_ts


def build_transfer_history_pages(
    transfers: Sequence["TransferHistory"],
    coin_name: str | None,
    is_v2: bool = False,
) -> list[str]:
    """Build paginated description pages for transfers history.

    Args:
        transfers: List of transfer history records
        coin_name: Name of the coin currency
        current_user_level: User's current level (to highlight with arrow)
        is_v2: Whether to use v2 description limit

    Returns:
        List of paginated strings
    """

    pages: list[str] = []
    current = ""
    levels_in_current_page = 0

    levels_per_page = 20
    limit = config.bot.EMBED_DESCRIPTION_LIMIT

    if is_v2:
        limit = config.bot.VIEW_V2_DESCRIPTION_LIMIT

    ...
    current = ""
    for transfer in transfers:
        line = f"Дата: {discord_ts(transfer.created_at, style='d')} | <@{transfer.user_id}> <:42920arrowrightalt:1421170550759489616> <@{transfer.receiver_id}> | {transfer.amount} {coin_name or 'коинов'}\n"  # noqa: E501

        if (len(current) + len(line) >= limit) or (
            levels_in_current_page >= levels_per_page
        ):
            pages.append(current)
            current = ""
            levels_in_current_page = 0

        current += line
        levels_in_current_page += 1

    if current:
        pages.append(current)

    if not pages:
        pages = ["История переводов пуста."]

    return pages
