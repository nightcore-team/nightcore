"""Add new battlepass level command."""

from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.models._annot import BattlepassLevelAnnot
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


@battlepass_group.command(name="add_level")
@app_commands.describe(
    required_exp="Количество EXP для этого уровня",
    reward_type="Тип награды",
    reward_amount="Количество",
)
@app_commands.choices(
    reward_type=BATTLEPASS_REWARDS_CHOICES,
)
async def add_level(
    interaction: Interaction["Nightcore"],
    required_exp: app_commands.Range[int, 1, 1000000],
    reward_type: app_commands.Choice[str],
    reward_amount: int,
):
    """Add new battle pass level."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    try:
        reward_amount = int(reward_amount)
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

    outcome = ""

    battlepass_level: BattlepassLevelAnnot = {
        "exp_required": required_exp,
    }  # type: ignore

    match reward_type.value:
        case "coins":
            battlepass_level["reward"] = {
                "name": "coins",
                "amount": reward_amount,
            }
        case "coins_case":
            battlepass_level["reward"] = {
                "name": "coins_case",
                "amount": reward_amount,
            }
        case "colors_case":
            battlepass_level["reward"] = {
                "name": "colors_case",
                "amount": reward_amount,
            }
        case "exp":
            battlepass_level["reward"] = {
                "name": "exp",
                "amount": reward_amount,
            }
        case _:
            outcome = "invalid_reward_type"

    if not outcome:
        async with specified_guild_config(
            bot, guild.id, GuildEconomyConfig
        ) as (
            guild_config,
            _,
        ):
            level = len(guild_config.battlepass_rewards) + 1
            battlepass_level["level"] = level

            # append
            guild_config.battlepass_rewards.append(battlepass_level)

            # sort by level number
            guild_config.battlepass_rewards.sort(
                key=lambda x: x.get("level", 0)
            )

            attributes.flag_modified(guild_config, "battlepass_rewards")

            outcome = "success"

    if outcome == "invalid_reward_type":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка добавления уровня",
                "Неверный тип награды.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        return await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Уровень добавлен",
                f"Уровень {level} успешно добавлен в боевой пропуск.",  # type: ignore
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
