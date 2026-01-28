"""Subcommand to change a battle pass level."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.config.config import config
from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.operations import (
    get_battlepass_level,
    get_case_by_id,
    get_color_by_id,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
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
    name="change_level", description="Изменить уровень боевого пропуска"
)  # type: ignore
@app_commands.describe(
    new_required_exp="Новое количество EXP для этого уровня",
    new_reward_type="Новый тип награды",
    new_reward_amount="Новое количество",
)
@app_commands.autocomplete(new_reward=reward_depends_on_type_autocomplete)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_CONFIG_ACCESS)
async def change_level(
    interaction: Interaction["Nightcore"],
    level: app_commands.Range[int, 1, 1000000],
    new_required_exp: app_commands.Range[int, 1, 1000000] | None = None,
    new_reward_type: CaseDropTypeEnum | None = None,
    new_reward_amount: app_commands.Range[int, 1, 1000000] | None = None,
    new_reward: str | None = None,
):
    """Change battle pass level."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    if (
        new_required_exp is None
        and new_reward_type is None
        and new_reward_amount is None
    ):
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Вы не выбрали ни одного параметра для изменения.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if (
        new_reward is None
        and new_reward_type is not None
        and new_reward_type.requires_id_or_custom()
    ):
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Для типов CASE, COLOR, CUSTOM ввод новой награды обязателен.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if (
        new_reward is not None
        and len(new_reward) > config.bot.MAX_CUSTOM_REWARD_SIZE
    ):
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Максимальная длина награды - 100 символов.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if new_reward_type is not None and new_reward_type.requires_id():
        try:
            new_reward_id = int(new_reward)  # type: ignore
        except ValueError as _:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Введен неверный id кейса или цвета.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

    outcome = ""

    async with bot.uow.start() as session:
        battlepass_level = await get_battlepass_level(
            session, guild_id=guild.id, level=level
        )
        if battlepass_level is None:
            outcome = "level_not_found"
        else:
            if new_required_exp is not None:
                battlepass_level.exp_required = new_required_exp

            if new_reward_type is not None:
                battlepass_level.reward["type"] = new_reward_type.value

                match new_reward_type:
                    case CaseDropTypeEnum.CUSTOM:
                        battlepass_level.reward["name"] = new_reward  # type: ignore
                    case CaseDropTypeEnum.COLOR:
                        color = await get_color_by_id(
                            session,
                            guild_id=guild.id,
                            color_id=new_reward_id,  # type: ignore
                        )

                        if color is None:
                            outcome = "drop_with_entered_id_not_found"
                        else:
                            battlepass_level.reward["drop_id"] = color.id

                    case CaseDropTypeEnum.CASE:
                        case = await get_case_by_id(
                            session,
                            guild_id=guild.id,
                            case_id=new_reward_id,  # type: ignore
                        )

                        if case is None:
                            outcome = "drop_with_entered_id_not_found"
                        else:
                            battlepass_level.reward["drop_id"] = case.id
                    case _:
                        pass

            if new_reward_amount is not None:
                battlepass_level.reward["amount"] = new_reward_amount

            attributes.flag_modified(battlepass_level, "reward")

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

    if outcome == "drop_with_entered_id_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения уровня.",
                f"Награда с id {new_reward} не найдена.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    await interaction.response.send_message(
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
