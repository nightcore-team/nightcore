"""Command to change color."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.interactions import Interaction
from sqlalchemy.exc import IntegrityError

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.operations import get_color_by_id, get_specified_webhook
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.features.economy._groups import color as color_group
from src.nightcore.features.economy.events.dto.item_change import (
    ChangedRole,
    ItemChangeNotifyEventDTO,
)
from src.nightcore.features.economy.utils.autocomplete import (
    guild_colors_autocomplete,
)
from src.nightcore.utils.object import compare_top_roles
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer
from src.utils._enums import ChannelType, ItemChangeActionEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@color_group.command(name="change", description="Изменить цвет")  # type: ignore
@app_commands.autocomplete(color_id=guild_colors_autocomplete)
@app_commands.rename(color_id="color")
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def change_color(
    interaction: Interaction["Nightcore"],
    color_id: app_commands.Transform[int, StrToIntTransformer],
    new_role: discord.Role,
):
    """Change color."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    logging_webhook = None
    outcome = None
    before_role_id: int | None = None

    if new_role.position >= member.top_role.position:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения цвета",
                "Вы не можете использовать роль с позицией выше чем ваша высшая роль.",  # noqa: E501
            ),
            ephemeral=True,
        )
        return

    if new_role.permissions.administrator:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения цвета",
                "Роль цвета не может иметь права администратора.",
            ),
            ephemeral=True,
        )
        return

    if not compare_top_roles(guild, new_role):
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения цвета",
                "Роль цвета должна быть ниже высшей роли бота.",
            ),
            ephemeral=True,
        )
        return

    try:
        async with bot.uow.start() as session:
            color = await get_color_by_id(
                session, guild_id=guild.id, color_id=color_id
            )

            if color is None:
                outcome = "color_not_found"
            else:
                before_role_id = color.role_id
                color.role_id = new_role.id

            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

    except IntegrityError:
        outcome = "color_exists"

        logger.warning(
            "[color/change] Error changing color in guild %s with existing role %s",  # noqa: E501
            guild.id,
            new_role.id,
        )

    except Exception as e:
        outcome = "color_change_error"

        logger.exception(
            "[color/change] Error changing color in guild %s: %s",
            guild.id,
            e,
        )

    if outcome == "color_not_found":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения цвета",
                "Выбранный цвет не найден в базе данных.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "color_exists":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения цвета",
                "К данной роли уже привязан цвет.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "color_change_error":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения цвета",
                "Произошла ошибка при создании цвета. Обратитесь к разработчикам.",  # noqa: E501
            ),
            ephemeral=True,
        )
        return

    item = ChangedRole(before_id=before_role_id, after_id=new_role.id)  # type: ignore

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.COLOR_UPDATE,
        logging_webhook=logging_webhook,
        moderator_id=interaction.user.id,
        item_name=f"{new_role.mention} ({new_role.id})",
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    await interaction.response.send_message(
        view=SuccessViewV2(
            "Изменение цвета успешно",
            f"Вы успешно изменили цвет {new_role.mention} ",
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked guild=%s role_id=%s", guild.id, new_role.id
    )
