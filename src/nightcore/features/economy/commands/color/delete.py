"""Command to delete color."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType, ItemChangeActionEnum
from src.infra.db.operations import (
    get_color_by_id,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
)
from src.nightcore.components.embed.success import SuccessMoveEmbed
from src.nightcore.features.economy._groups import color as color_group
from src.nightcore.features.economy.events.dto.item_change import (
    ChangedRole,
    ItemChangeNotifyEventDTO,
)
from src.nightcore.features.economy.utils.autocomplete import (
    guild_colors_autocomplete,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@color_group.command(name="delete", description="Удалить цвет")  # type: ignore
@app_commands.rename(color_id="color")
@app_commands.autocomplete(color_id=guild_colors_autocomplete)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def delete_color(
    interaction: Interaction["Nightcore"],
    color_id: app_commands.Transform[int, StrToIntTransformer],
):
    """Delete color."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""
    logging_channel_id = None

    try:
        async with bot.uow.start() as session:
            color = await get_color_by_id(
                session, guild_id=guild.id, color_id=color_id
            )

            if color is None:
                outcome = "color_not_found"
            else:
                await session.delete(color)

                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_ECONOMY,
                )

    except Exception as e:
        outcome = "color_delete_error"

        logger.exception(
            "[color/delete] Error delete color in guild %s: %s",
            guild.id,
            e,
        )

    if outcome == "color_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения цвета",
                "Выбранный цвет не найден в базе данных.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "color_delete_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления цвета",
                "Произошла ошибка при удалении цвета. Обратитесь к разработчикам.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    item = ChangedRole(
        after_id=color.role_id,  # type: ignore
    )

    color_role = guild.get_role(color.role_id)  # type: ignore

    color_name = color_role.mention if color_role else "unknown"

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.DELETE,
        logging_channel_id=logging_channel_id,
        moderator_id=interaction.user.id,
        item_name=f"{color_name} ({color.role_id})",  # type: ignore
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Удаление цвета успешно",
            f"Вы успешно удалили цвет <@&{color.role_id}> ",  # type: ignore
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked guild=%s user=%s color_id=%s",
        guild.id,
        interaction.user.id,
        color_id,
    )
