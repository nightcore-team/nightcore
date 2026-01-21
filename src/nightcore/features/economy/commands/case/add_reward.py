"""Command to add case reward."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._annot import CaseDropAnnot
from src.infra.db.models._enums import (
    CaseDropTypeEnum,
    ChannelType,
    ItemChangeActionEnum,
)
from src.infra.db.operations import (
    get_case_by_id,
    get_color_by_id,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
)
from src.nightcore.components.embed.error import ValidationErrorEmbed
from src.nightcore.components.embed.success import SuccessMoveEmbed
from src.nightcore.features.economy._groups import case as case_group
from src.nightcore.features.economy.events.dto.item_change import (
    ChangedReward,
    ItemChangeNotifyEventDTO,
)
from src.nightcore.features.economy.utils.autocomplete import (
    reward_depends_on_type_autocomplete,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@case_group.command(name="add_reward", description="Добавить награду в кейс")  # type: ignore
@app_commands.describe(
    reward_type="Тип награды",
    reward_amount="Количество",
    weight="Вес награды (не является шансом выпадения)",
    reward="Выбор кейса / цвета / ввод текста, в зависимости от типа награды",
)
@app_commands.rename(case_id="case")
@app_commands.autocomplete(reward=reward_depends_on_type_autocomplete)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def add_case_reward(
    interaction: Interaction["Nightcore"],
    case_id: app_commands.Transform[int, StrToIntTransformer],
    reward_type: CaseDropTypeEnum,
    weight: app_commands.Range[int, 1, 1000000],
    amount: app_commands.Range[int, 1, 1000000],
    reward: str | None = None,
):
    """Add reward to case."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""
    logging_channel_id = None

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

    async with bot.uow.start() as session:
        try:
            case = await get_case_by_id(
                session, guild_id=guild.id, case_id=case_id
            )

            if case is None:
                outcome = "case_not_found"
            else:
                if len(case.drop) >= 30:
                    outcome = "max_rewards_achieved"
                else:
                    new_reward = CaseDropAnnot(
                        type=reward_type, amount=amount, chance=weight
                    )  # type: ignore

                    match reward_type:
                        case CaseDropTypeEnum.CASE:
                            reward_case = await get_case_by_id(
                                session,
                                guild_id=guild.id,
                                case_id=reward_id,  # type: ignore
                            )

                            if reward_case is None:
                                outcome = "unknown_reward_case_id"
                            else:
                                new_reward["drop_id"] = case.id
                                new_reward["name"] = case.name

                        case CaseDropTypeEnum.COLOR:
                            color = await get_color_by_id(
                                session,
                                guild_id=guild.id,
                                color_id=reward_id,  # type: ignore
                            )

                            if color is None:
                                outcome = "unknown_color_id"
                            else:
                                new_reward["drop_id"] = color.id
                                new_reward["name"] = str(color.role_id)
                        case CaseDropTypeEnum.CUSTOM:
                            new_reward["drop_id"] = None
                            new_reward["name"] = reward  # type: ignore
                        case _:
                            new_reward["drop_id"] = None
                            new_reward["name"] = reward_type.name

                    if not outcome:
                        case.drop.append(new_reward)

                        attributes.flag_modified(case, "drop")

                        logging_channel_id = await get_specified_channel(
                            session,
                            guild_id=guild.id,
                            config_type=GuildLoggingConfig,
                            channel_type=ChannelType.LOGGING_ECONOMY,
                        )

        except Exception as e:
            outcome = "case_change_error"

            logger.exception(
                "[case/add_reward] Error creating reward in guild %s: %s",
                guild.id,
                e,
            )

    if outcome == "case_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения кейса",
                "Выбранный кейс не найден в базе данных.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "case_change_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения кейса",
                "Произошла ошибка при изменении кейса. Обратитесь к разработчикам.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "max_rewards_achieved":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения кейса",
                "Достигнуто максимально количество наград в кейсе.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "unknown_reward_case_id":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка добавления награды",
                "Кейс с данным id не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "unknown_color_id":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка добавления награды",
                "Цвет с данным id не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    item = ChangedReward(after=new_reward)  # type: ignore

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.ADD_REWARD,
        logging_channel_id=logging_channel_id,
        moderator_id=interaction.user.id,
        item_name=case.name,  # type: ignore
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Добавление награды успешно",
            f"Вы добавили награду в кейс {case.name} ",  # type: ignore
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked guild=%s user=%s case_name=%s",
        guild.id,
        interaction.user.id,
        case.name,  # type: ignore
    )
