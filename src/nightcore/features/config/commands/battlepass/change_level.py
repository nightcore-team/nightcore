"""Subcommand to change a battle pass level."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildEconomyConfig
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.battlepass.utils.types import (
    BATTLEPASS_REWARDS_CHOICES,
)
from src.nightcore.features.config._groups import (
    battlepass as battlepass_group,
)
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


@battlepass_group.command(
    name="change_level", description="Изменить уровень боевого пропуска"
)  # type: ignore
@app_commands.describe(
    new_required_exp="Новое количество EXP для этого уровня",
    new_reward_type="Новый тип награды",
    new_reward_amount="Новое количество",
)
@app_commands.choices(
    new_reward_type=BATTLEPASS_REWARDS_CHOICES,
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def change_level(
    interaction: Interaction["Nightcore"],
    level: int,
    new_required_exp: app_commands.Range[int, 1, 1000000] | None = None,
    new_reward_type: app_commands.Choice[str] | None = None,
    new_reward_amount: int | None = None,
):
    """Change battle pass level."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    if new_reward_amount:
        try:
            reward_amount = int(new_reward_amount)
            if reward_amount <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Пожалуйста, введите положительное целое число.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

    try:
        int_level = int(level)
    except ValueError:
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Пожалуйста, введите действительный номер уровня.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    outcome = ""

    async with specified_guild_config(
        bot, guild.id, GuildEconomyConfig, _create=True
    ) as (
        guild_config,
        _,
    ):
        for bp_level in guild_config.battlepass_rewards or []:
            if bp_level["level"] == int_level:
                if new_required_exp is not None:
                    bp_level["exp_required"] = new_required_exp

                if new_reward_type is not None:
                    if new_reward_amount is None:
                        outcome = "new_reward_without_amount"
                        break

                    match new_reward_type.value:
                        case "coins":
                            bp_level["reward"] = {
                                "name": "coins",
                                "amount": new_reward_amount,
                            }
                        case "coins_case":
                            bp_level["reward"] = {
                                "name": "coins_case",
                                "amount": new_reward_amount,
                            }
                        case "colors_case":
                            bp_level["reward"] = {
                                "name": "colors_case",
                                "amount": new_reward_amount,
                            }
                        case _:
                            outcome = "invalid_reward_type"
                            break

                break
        else:
            outcome = "level_not_found"

        if not outcome:
            attributes.flag_modified(guild_config, "battlepass_rewards")
            outcome = "success"

    if outcome == "level_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения уровня.",
                f"Уровень {level} не найден в боевом пропуске.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "invalid_reward_type":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка добавления уровня.",
                "Неверный тип награды.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "new_reward_without_amount":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения уровня.",
                "Для изменения награды необходимо указать новое количество.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        return await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Уровень изменен.",
                f"Уровень {level} успешно изменен в боевой пропуск.",  # type: ignore
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    logger.info(
        "[command] - invoked user=%s guild=%s change_level=%s required_exp=%s reward_type=%s reward_amount=%s",  # noqa: E501
        interaction.user.id,
        guild.id,
        level,
        new_required_exp,
        new_reward_type,
        new_reward_amount,
    )
