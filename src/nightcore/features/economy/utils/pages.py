"""Build transfers history pages."""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from discord.ui import TextDisplay

from src.config.config import config
from src.infra.db.models.battlepass_level import BattlepassLevel

if TYPE_CHECKING:
    from src.infra.db.models import TransferHistory

from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.models.case import Case
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
        line = f"Дата: {discord_ts(transfer.created_at, style='d')} | <@{transfer.user_id}> <:42920arrowrightalt:1442924551880314921> <@{transfer.receiver_id}> | {transfer.amount} {coin_name or 'коинов'}\n"  # noqa: E501

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


def build_cases_help_pages(
    cases: Sequence[Case],
) -> list[list[TextDisplay[Any]]]:
    """Build paginated pages for case help command."""

    pages: list[list[TextDisplay[Any]]] = []

    for case in cases:
        page: list[TextDisplay[Any]] = []

        page.append(
            TextDisplay(f"### {case.name}"),
        )
        if len(case.drop) < 1:
            page.append(TextDisplay("> В данный момент кейс не настроен."))
        else:
            # Calculate total weight to convert weights to percentages
            total_weight = sum(drop["chance"] for drop in case.drop)

            page.append(
                TextDisplay(
                    "\n".join(
                        f"> {i}. {drop['amount'] if drop['type'] != CaseDropTypeEnum.COLOR.value else ''} {drop['name']} "  # noqa: E501
                        f"- шанс **`{drop['chance'] / total_weight * 100:.2f}%`**"  # noqa: E501
                        for i, drop in enumerate(case.drop, start=1)
                    )
                ),
            )

        pages.append(page)

    if not pages:
        pages = [[TextDisplay[Any]("Кейсы не настроены")]]

    return pages


def build_battlepass_levels_pages(
    levels: Sequence[BattlepassLevel],
    coin_name: str | None = None,
    current_user_level: int | None = None,
    is_v2: bool = False,
) -> list[str]:
    """Build paginated description pages for battlepass levels.

    Args:
        levels: List of battlepass levels
        coin_name: Name of the coin currency
        current_user_level: User's current level (to highlight with arrow)
        is_v2: Whether to use v2 description limit

    Returns:
        List of paginated strings (20 levels per page)
    """

    pages: list[str] = []
    current = ""
    levels_in_current_page = 0

    levels_per_page = 20
    limit = config.bot.EMBED_DESCRIPTION_LIMIT

    if is_v2:
        limit = config.bot.VIEW_V2_DESCRIPTION_LIMIT

    for level_data in levels:
        level = level_data.level
        exp_required = level_data.exp_required

        reward_name = level_data.reward["name"]
        reward_amount = level_data.reward["amount"]

        arrow = (
            "<:48765whitearrow:1442918703367983225> "
            if level == current_user_level
            else ""
        )

        line = f"**{arrow}Уровень {level}** - `{exp_required} BP points` - **Награда**: {reward_name}, {reward_amount}\n"  # noqa: E501

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
        pages = ["Уровни боевого пропуска не настроены."]

    return pages
