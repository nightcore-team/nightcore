"""Command to change case."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction
from sqlalchemy.exc import IntegrityError

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType, ItemChangeActionEnum
from src.infra.db.operations import get_case_by_id, get_specified_channel
from src.nightcore.components.embed import (
    ErrorEmbed,
)
from src.nightcore.components.embed.success import SuccessMoveEmbed
from src.nightcore.features.economy._groups import case as case_group
from src.nightcore.features.economy.events.dto.item_change import (
    ChangedCase,
    ItemChangeNotifyEventDTO,
)
from src.nightcore.features.economy.utils.autocomplete import (
    guild_cases_autocomplete,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@case_group.command(name="change", description="Изменить кейс")  # type: ignore
@app_commands.rename(case_id="case")
@app_commands.autocomplete(case_id=guild_cases_autocomplete)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def change_case(
    interaction: Interaction["Nightcore"],
    case_id: app_commands.Transform[int, StrToIntTransformer],
    new_case_name: app_commands.Range[str, 100],
):
    """Change case."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""
    old_name = ""
    logging_channel_id = None

    try:
        async with bot.uow.start() as session:
            case = await get_case_by_id(
                session, guild_id=guild.id, case_id=case_id
            )

            if case is None:
                outcome = "case_not_found"
            else:
                old_name = case.name

                case.name = new_case_name

                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_ECONOMY,
                )

    except IntegrityError:
        outcome = "case_name_exists"

        logger.warning(
            "[case/change] Error changing case in guild %s, name exists %s",
            guild.id,
            new_case_name,
        )

    except Exception as e:
        outcome = "case_change_error"

        logger.exception(
            "[case/change] Error creating case in guild %s: %s",
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

    if outcome == "case_name_exists":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка создания кейса",
                "Кейс с данным названием уже существует.",
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

    item = ChangedCase(
        before_name=old_name,
        after_name=case.name,  # type: ignore
    )

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.CASE_UPDATE,
        logging_channel_id=logging_channel_id,
        moderator_id=interaction.user.id,
        item_name=case.name,  # type: ignore
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Создание кейса успешно",
            f"Вы успешно изменили название кейса {case.name} ",  # type: ignore
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
