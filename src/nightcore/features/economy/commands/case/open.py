"""Open case command."""

import logging
import random
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.models._annot import CoinDropAnnot, ColorDropAnnot
from src.infra.db.operations import get_or_create_user
from src.nightcore.components.embed import (
    ErrorEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.economy._groups import case as case_group
from src.nightcore.features.economy.components.v2 import CaseOpenViewV2
from src.nightcore.features.economy.utils import cases_autocomplete
from src.nightcore.features.economy.utils.case import CASES_NAMES
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


def open_coins_case(drops: list[CoinDropAnnot]) -> tuple[int, int]:
    """Open coins case and get reward.

    Args:
        drops: List of coin drops with amount and chance

    Returns:
        Tuple of (coins_amount, drop_chance)
    """
    if not drops:
        raise ValueError("Case has no drops configured")

    amounts = [drop["amount"] for drop in drops]
    chances = [drop["chance"] for drop in drops]

    # Weighted random choice
    selected_amount = random.choices(amounts, weights=chances, k=1)[0]

    # Get chance of this drop
    drop = next(d for d in drops if d["amount"] == selected_amount)

    return selected_amount, drop["chance"]


def open_colors_case(drops: dict[str, ColorDropAnnot]) -> tuple[str, int, int]:
    """Open colors case and get reward.

    Args:
        drops: Dictionary of color drops with role_id and chance

    Returns:
        Tuple of (color_key, role_id, chance)
        Example: ("color_1", 1433436907865378800, 20)
    """
    if not drops:
        raise ValueError("Case has no drops configured")

    color_keys = list(drops.keys())
    role_ids = [drop["role_id"] for drop in drops.values()]
    chances = [drop["chance"] for drop in drops.values()]

    selected_index = random.choices(range(len(drops)), weights=chances, k=1)[0]

    color_key = color_keys[selected_index]
    role_id = role_ids[selected_index]
    chance = chances[selected_index]

    return color_key, role_id, chance


@case_group.command(name="open", description="Открыть кейс.")
@app_commands.describe(case="Кейс для открытия.")
@app_commands.autocomplete(case=cases_autocomplete)
async def open_case(
    interaction: Interaction["Nightcore"],
    case: str,
):
    """Open case and get reward."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    outcome = ""
    reward_text = ""
    coins_reward = 0
    color_role_id = 0
    color_name = ""
    chance = 0

    async with specified_guild_config(
        bot, guild_id=guild.id, config_type=GuildEconomyConfig
    ) as (guild_config, session):
        try:
            user, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=member.id,
            )

            case_count = user.inventory.get("cases", {}).get(case, 0)

            if case_count <= 0:
                outcome = "no_case"

            else:
                match case:
                    case "coins_case":
                        if not guild_config.drop_from_coins_case:
                            outcome = "case_not_configured"
                        else:
                            coins_reward, chance = open_coins_case(
                                guild_config.drop_from_coins_case
                            )

                            user.coins += coins_reward

                            # remove case from inventory
                            user.inventory["cases"][case] -= 1  # type: ignore
                            if user.inventory["cases"][case] <= 0:  # type: ignore
                                del user.inventory["cases"][case]  # type: ignore

                            attributes.flag_modified(user, "inventory")

                            coin_name = guild_config.coin_name or "коинов"
                            reward_text = f"{coins_reward} {coin_name}"
                            outcome = "success"

                    case "colors_case":
                        if not guild_config.drop_from_colors_case:
                            outcome = "case_not_configured"
                        else:
                            color_name, color_role_id, chance = (
                                open_colors_case(
                                    guild_config.drop_from_colors_case
                                )
                            )

                            if "colors" not in user.inventory:
                                user.inventory["colors"] = []

                            if color_name in user.inventory["colors"]:
                                pass
                            else:
                                user.inventory["colors"].append(color_name)

                            # remove case from inventory
                            user.inventory["cases"][case] -= 1  # type: ignore
                            if user.inventory["cases"][case] <= 0:  # type: ignore
                                del user.inventory["cases"][case]  # type: ignore

                            attributes.flag_modified(user, "inventory")

                            reward_text = f"цвет <@&{color_role_id}>"
                            outcome = "success"

                    case _:
                        outcome = "unknown_case"

        except Exception as e:
            logger.exception(
                "[case/open] Error opening case %s for user %s in guild %s: %s",  # noqa: E501
                case,
                member.id,
                guild.id,
                e,
            )
            outcome = "error"

    if outcome == "no_case":
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "У вас нет такого кейса для открытия.",  # noqa: RUF001
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "case_not_configured":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка открытия кейса",
                "Этот кейс не настроен на этом сервере.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "unknown_case":
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Неизвестный тип кейса.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка открытия кейса",
                "Произошла ошибка при открытии кейса.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        # TODO: make more beautiful view for case opening
        view = CaseOpenViewV2(
            bot=bot,
            case_name=CASES_NAMES.get(case, case).lower(),
            reward=reward_text,
            chance=chance,
        )
        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )

        logger.info(
            "[case/open] User %s opened case %s in guild %s, got reward: %s",
            member.id,
            case,
            guild.id,
            reward_text,
        )
