"""Subcommand to add a new battle pass level."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models._annot import BattlepassRewardAnnot
from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.models.battlepass_level import BattlepassLevel
from src.infra.db.operations import (
    get_battlepass_level,
    get_case_by_id,
    get_color_by_id,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.components.embed.error import ValidationErrorEmbed
from src.nightcore.features.config._groups import (
    battlepass as battlepass_group,
)
from src.nightcore.features.config.utils.autocomplete import (
    reward_depends_on_type_autocomplete,
)

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
    exp_required="Количество EXP для этого уровня",
    reward_type="Тип награды",
    reward_amount="Количество",
    reward="Выбор кейса / цвета / ввод текста, в зависимости от типа награды",
    before_level="Номер уровня для добавления нового перед ним",
)
@app_commands.autocomplete(reward=reward_depends_on_type_autocomplete)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_CONFIG_ACCESS)
async def add_level(
    interaction: Interaction["Nightcore"],
    exp_required: app_commands.Range[int, 1, 1000000],
    reward_type: CaseDropTypeEnum,
    reward_amount: app_commands.Range[int, 1, 1000000],
    reward: str | None = None,
    before_level: app_commands.Range[int, 1, 10000] | None = None,
):
    """Add new battle pass level."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""

    if reward is None and reward_type.requires_id_or_custom():
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Для типов CASE, COLOR, CUSTOM ввод награды обязателен.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if reward_type.requires_id():
        try:
            reward_id = int(reward)  # type: ignore
        except ValueError as _:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Введен неверный id кейса или цвета.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

    battlepass_level = BattlepassLevel(
        guild_id=guild.id, exp_required=exp_required
    )

    battlepass_level.reward = BattlepassRewardAnnot(
        type=reward_type.value,
        drop_id=-1,
        name=reward_type.to_str(),
        amount=reward_amount,
    )

    if not outcome:
        async with bot.uow.start() as session:
            before_level_exists = (
                await get_battlepass_level(
                    session, guild_id=guild.id, level=before_level
                )
                is not None
                if before_level is not None
                else False
            )

            match reward_type:
                case CaseDropTypeEnum.CASE:
                    case = await get_case_by_id(
                        session,
                        guild_id=guild.id,
                        case_id=reward_id,  # type: ignore
                    )

                    if case is None:
                        outcome = "unknown_case_id"
                    else:
                        battlepass_level.reward["drop_id"] = case.id

                case CaseDropTypeEnum.COLOR:
                    color = await get_color_by_id(
                        session,
                        guild_id=guild.id,
                        color_id=reward_id,  # type: ignore
                    )

                    if color is None:
                        outcome = "unknown_color_id"
                    else:
                        battlepass_level.reward["drop_id"] = color.id
                case CaseDropTypeEnum.CUSTOM:
                    battlepass_level.reward["name"] = reward  # type: ignore
                case _:
                    ...

            if not outcome:
                if before_level and before_level_exists:
                    battlepass_level.level = before_level

                    session.add(battlepass_level)

                    outcome = "success"
                elif before_level is None:
                    session.add(battlepass_level)

                    outcome = "success"
                else:
                    outcome = "before_level_not_found"

    if outcome == "before_level_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка добавления уровня",
                "Предыдущий уровень для добавления не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

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
                "Уровень успешно добавлен в боевой пропуск.",  # type: ignore
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    logger.info(
        "[command] - invoked user=%s guild=%s required_exp=%s reward_type=%s reward_amount=%s",  # noqa: E501
        interaction.user.id,
        guild.id,
        exp_required,
        reward_type.value,
        reward_amount,
    )
