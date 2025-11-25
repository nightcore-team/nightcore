"""Build battlepass levels pages."""

from src.config.config import config
from src.infra.db.models._annot import BattlepassLevelAnnot

from .types import BATTLEPASS_REWARDS


def build_battlepass_levels_pages(
    levels: list[BattlepassLevelAnnot],
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

    # Сортуємо рівні по номеру (на всяк випадок)
    sorted_levels = sorted(levels, key=lambda x: x["level"])

    for level_data in sorted_levels:
        level = level_data["level"]
        exp_required = level_data["exp_required"]

        reward_type = BATTLEPASS_REWARDS[level_data["reward"]["name"]]
        reward_amount = level_data["reward"]["amount"]

        if reward_type == "коины":
            reward_type = coin_name or "коины"

        arrow = (
            "<:48765whitearrow:1442918703367983225> "
            if level == current_user_level
            else ""
        )

        line = f"**{arrow}Уровень {level}** - `{exp_required} BP points` - **Награда**: {reward_type}, {reward_amount}\n"  # noqa: E501

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
