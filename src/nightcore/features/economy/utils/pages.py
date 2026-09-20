"""Build transfers history pages."""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from discord.ui import TextDisplay

from src.config.config import config
from src.infra.db.models._annot import UserVipStatusAnnot
from src.infra.db.models.battlepass_level import BattlepassLevel

if TYPE_CHECKING:
    from src.infra.db.models import TransferHistory
    from src.infra.db.models.user import UserVipStatus

from src.infra.db.models.case import Case
from src.infra.db.models.vip import VipStatus
from src.nightcore.utils import discord_ts
from src.utils._enums import CaseDropTypeEnum

VIP_STATUSES_PER_PAGE = 4


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


def build_vip_statuses_content(
    vip_statuses: Sequence[VipStatus],
) -> list[TextDisplay[Any]]:
    """Build the display content for VIP statuses."""
    content: list[TextDisplay[Any]] = []
    for vip in vip_statuses:
        content.append(
            TextDisplay(
                f"### {vip.emoji_str if vip.emoji_str else ''} {vip.name}"
            ),
        )

        perks: list[str] = []

        if vip.deposit_max_balance:
            perks.append(
                f"> <:nightcoreInfinity:1551210202953547806> Лимит баланса депозитного счёта: **`{vip.deposit_max_balance}`**"  # noqa: E501
            )

        if vip.deposit_interest_rate:
            rate = float(vip.deposit_interest_rate) * 100
            perks.append(
                f"> <:nightcorePercent:1545112163742519349> Процентная ставка по депозиту: **`{rate:.2f}%`**"  # noqa: E501
            )

        if vip.deposit_interest_cap_amount:
            perks.append(
                f"> <:nightcoreInfinity:1551210202953547806> Лимит начисления процентов: **`{vip.deposit_interest_cap_amount}`**"  # noqa: E501
            )

        if vip.shop_discount:
            discount = float(vip.shop_discount) * 100
            perks.append(
                f"> <:nightcoreShopDiscount:1551212187614453820> Скидка в магазине: **`{discount:.2f}%`**"  # noqa: E501
            )

        if not perks:
            content.append(
                TextDisplay("> Преимущества данного VIP-статуса не настроены.")
            )
        else:
            content.append(TextDisplay("\n".join(perks)))

    return content


def build_vip_statuses_help_pages(
    vip_statuses: Sequence[VipStatus], vip_statuses_per_page: int = 3
) -> list[list[TextDisplay[Any]]]:
    """Build paginated pages for VIP-statuses help command."""

    content = build_vip_statuses_content(vip_statuses)

    pages = [
        content[index : index + vip_statuses_per_page]
        for index in range(0, len(content), vip_statuses_per_page)
    ]

    if not pages:
        pages = [[TextDisplay[Any]("VIP-статусы не настроены")]]

    return pages


def build_user_vip_statuses_content(
    user_vip_statuses: Sequence["UserVipStatus"],
    guild_vip_statuses: Sequence[VipStatus],
) -> tuple[list[TextDisplay[Any]], list[UserVipStatusAnnot]]:
    """Build content and statuses for a user's own VIP-statuses.

    Also used after activation to rebuild the view with updated button states.

    Returns:
        Tuple of display content and the matching list of statuses.
    """

    config_by_id = {status.id: status for status in guild_vip_statuses}

    owned_configs: list[VipStatus] = []
    statuses: list[UserVipStatusAnnot] = []

    for user_vip in user_vip_statuses:
        config = config_by_id.get(user_vip.vip_id)
        if config is None:
            continue

        owned_configs.append(config)
        statuses.append(
            {
                "vip_id": user_vip.vip_id,
                "name": config.name,
                "emoji_str": config.emoji_str,
                "is_active": user_vip.is_active,
            }
        )

    return build_vip_statuses_content(owned_configs), statuses


def build_battlepass_levels_pages(
    levels: Sequence[BattlepassLevel],
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
            "<:nightcoreArrowRightCyan:1540434390780477551> "
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
