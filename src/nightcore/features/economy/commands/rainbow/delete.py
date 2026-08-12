"""Command to delete rainbow role."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.operations import (
    get_rainbow_role_by_guild,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
)
from src.nightcore.components.embed.success import SuccessMoveEmbed
from src.nightcore.features.economy._groups import rainbow as rainbow_group
from src.nightcore.features.economy.events.dto.item_change import (
    ChangedRole,
    ItemChangeNotifyEventDTO,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import ChannelType, ItemChangeActionEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@rainbow_group.command(name="delete", description="Удалить радужную роль")  # type: ignore
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def delete_rainbow(
    interaction: Interaction["Nightcore"],
):
    """Delete rainbow role."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""
    logging_channel_id = None

    try:
        async with bot.uow.start() as session:
            rainbow = await get_rainbow_role_by_guild(
                session, guild_id=guild.id
            )

            if rainbow is None:
                outcome = "rainbow_not_found"
            else:
                await session.delete(rainbow)

                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_ECONOMY,
                )

    except Exception as e:
        outcome = "rainbow_delete_error"

        logger.exception(
            "[rainbow/delete] Error delete rainbow role in guild %s: %s",
            guild.id,
            e,
        )

    if outcome == "rainbow_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления радужной роли",
                "На этом сервере не настроена радужная роль.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "rainbow_delete_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления радужной роли",
                "Произошла ошибка при удалении радужной роли. Обратитесь к разработчикам.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    item = ChangedRole(
        after_id=rainbow.role_id,  # type: ignore
    )

    rainbow_role = guild.get_role(rainbow.role_id)  # type: ignore

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Удаление радужной роли успешно",
            f"Вы успешно удалили радужную роль <@&{rainbow.role_id}> ",  # type: ignore
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    rainbow_name = rainbow_role.mention if rainbow_role else "unknown"

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.DELETE,
        logging_channel_id=logging_channel_id,
        moderator_id=interaction.user.id,
        item_name=f"{rainbow_name} ({rainbow.role_id})",  # type: ignore
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    logger.info(
        "[command] - invoked guild=%s user=%s",
        guild.id,
        interaction.user.id,
    )
