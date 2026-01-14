"""Subcommand to add a new battle pass level."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.models._annot import (
    BattlepassLevelAnnot,
)
from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.operations import get_case_by_id, get_color_by_id
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.config._groups import (
    battlepass as battlepass_group,
)
from src.nightcore.features.config.utils.autocomplete import (
    reward_depends_on_type_autocomplete,
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
    name="add_level", description="Добавить уровень боевого пропуска"
)  # type: ignore
@app_commands.describe(
    required_exp="Количество EXP для этого уровня",
    reward_type="Тип награды",
    reward_amount="Количество",
    reward="Выбор кейса или цвета, в зависимости от типа награды",
)
@app_commands.autocomplete(reward=reward_depends_on_type_autocomplete)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_CONFIG_ACCESS)
async def add_level(
    interaction: Interaction["Nightcore"],
    required_exp: app_commands.Range[int, 1, 1000000],
    reward_type: CaseDropTypeEnum,
    reward_amount: app_commands.Range[int, 1, 1000000],
    reward: app_commands.Choice[str] | None = None,
):
    """Add new battle pass level."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""

    battlepass_level: BattlepassLevelAnnot = {
        "exp_required": required_exp,
    }  # type: ignore

    match reward_type:
        case CaseDropTypeEnum.CASE:
            if reward is None:
                outcome = "no_reward_in_input"
            else:
                battlepass_level["reward"] = {  # type: ignore
                    "drop_id": reward.value,
                }
        case CaseDropTypeEnum.COLOR:
            if reward is None:
                outcome = "no_reward_in_input"
            else:
                battlepass_level["reward"] = {  # type: ignore
                    "drop_id": reward.value,
                }
        case CaseDropTypeEnum.CUSTOM:
            battlepass_level["reward"] = {  # type: ignore
                "drop_id": None,
                "name": reward,
            }
        case _:
            battlepass_level["reward"] = {  # type: ignore
                "drop_id": None,
                "name": reward_type.name,
            }

    if outcome == "no_reward_in_input":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка добавления уровня",
                "Для данного типа награды необходимо выбрать кейс или цвет.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    battlepass_level["reward"]["amount"] = reward_amount  # type: ignore
    battlepass_level["reward"]["type"] = reward_type.value  # type: ignore

    if not outcome:
        async with specified_guild_config(
            bot, guild.id, GuildEconomyConfig, _create=True
        ) as (
            guild_config,
            session,
        ):
            if reward_type == CaseDropTypeEnum.CASE:
                case = await get_case_by_id(
                    session,
                    guild_id=guild.id,
                    case_id=reward.value,  # type: ignore
                )

                if case is None:
                    outcome = "unknown_case_id"
                else:
                    battlepass_level["reward"]["name"] = case.name  # type: ignore

            if reward_type == CaseDropTypeEnum.CASE:
                color = await get_color_by_id(
                    session,
                    guild_id=guild.id,
                    color_id=reward.value,  # type: ignore
                )

                if color is None:
                    outcome = "unknown_color_id"
                else:
                    battlepass_level["reward"]["name"] = str(color.role_id)  # type: ignore

            if not outcome:
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

    if outcome == "unknown_case_id":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка добавления уровня",
                "Кейс с данным id не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "unknown_color_id":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка добавления уровня",
                "Цвет с данным id не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Уровень добавлен",
                f"Уровень {level} успешно добавлен в боевой пропуск.",  # type: ignore
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    logger.info(
        "[command] - invoked user=%s guild=%s add_level=%s required_exp=%s reward_type=%s reward_amount=%s",  # noqa: E501
        interaction.user.id,
        guild.id,
        level,  # type: ignore
        required_exp,
        reward_type.value,
        reward_amount,
    )
