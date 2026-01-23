"""Command to create case."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction
from sqlalchemy.exc import IntegrityError

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType, ItemChangeActionEnum
from src.infra.db.models.case import Case
from src.infra.db.operations import get_specified_channel
from src.nightcore.components.embed import (
    ErrorEmbed,
)
from src.nightcore.components.embed.success import SuccessMoveEmbed
from src.nightcore.features.economy._groups import case as case_group
from src.nightcore.features.economy.events.dto.item_change import (
    ChangedCase,
    ItemChangeNotifyEventDTO,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@case_group.command(name="create", description="Создать кейс")  # type: ignore
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def create_case(
    interaction: Interaction["Nightcore"],
    case_name: app_commands.Range[str, 100],
):
    """Create case."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""
    logging_channel_id = None

    try:
        async with bot.uow.start() as session:
            new_case = Case(
                name=case_name,
                guild_id=guild.id,
            )

            session.add(new_case)

            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )
    except IntegrityError:
        outcome = "case_name_exists"

        logger.warning(
            "[case/create] Error creating case in guild %s, name exists %s",
            guild.id,
            case_name,
        )

    except Exception as e:
        outcome = "case_create_error"

        logger.exception(
            "[case/create] Error creating case in guild %s: %s",
            guild.id,
            e,
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

    if outcome == "case_create_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка создания кейса",
                "Произошла ошибка при создании кейса. Обратитесь к разработчикам.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    item = ChangedCase(
        after=new_case,  # type: ignore
    )

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.CREATE.value,
        logging_channel_id=logging_channel_id,
        moderator_id=interaction.user.id,
        item_name=case_name,
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Создание кейса успешно",
            f"Вы успешно создали кейс {case_name} ",
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked guild=%s user=%s case_name=%s",
        guild.id,
        interaction.user.id,
        case_name,
    )
