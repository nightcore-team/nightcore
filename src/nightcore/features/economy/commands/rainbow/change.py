"""Command to change rainbow role."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.operations import (
    get_rainbow_role_by_guild,
    get_specified_webhook,
)
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.features.economy._groups import rainbow as rainbow_group
from src.nightcore.features.economy.events.dto.item_change import (
    ChangedRole,
    ItemChangeNotifyEventDTO,
)
from src.nightcore.utils.object import compare_top_roles
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import (
    ChannelType,
    ItemChangeActionEnum,
    RainbowColorChangeTypeEnum,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@rainbow_group.command(name="change", description="Изменить радужную роль")  # type: ignore
@app_commands.describe(
    change_type=(
        "Тип смены цвета радужной роли (если не указан, останется прежним)"
    )
)
@app_commands.choices(
    change_type=[
        app_commands.Choice(
            name="Сдвиг (плавное изменение цвета)",
            value=RainbowColorChangeTypeEnum.OFFSET.value,
        ),
        app_commands.Choice(
            name="Рандом (случайный цвет из радуги)",
            value=RainbowColorChangeTypeEnum.RANDOM.value,
        ),
    ]
)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def change_rainbow(
    interaction: Interaction["Nightcore"],
    new_role: discord.Role,
    change_type: str | None = None,
):
    """Change rainbow role."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    logging_webhook = None
    outcome = ""

    if new_role.position >= member.top_role.position:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения радужной роли",
                "Вы не можете использовать роль с позицией выше чем ваша высшая роль.",  # noqa: E501
            ),
            ephemeral=True,
        )
        return

    if new_role.permissions.administrator:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения радужной роли",
                "Радужная роль не может иметь права администратора.",
            ),
            ephemeral=True,
        )
        return

    if not compare_top_roles(guild, new_role):
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения радужной роли",
                "Радужная роль должна быть ниже высшей роли бота.",
            ),
            ephemeral=True,
        )
        return

    try:
        async with bot.uow.start() as session:
            rainbow = await get_rainbow_role_by_guild(
                session, guild_id=guild.id
            )

            if rainbow is None:
                outcome = "rainbow_not_found"
            else:
                before_role_id = rainbow.role_id
                rainbow.role_id = new_role.id

                if change_type is not None:
                    rainbow.change_type = RainbowColorChangeTypeEnum(
                        change_type
                    )

                rainbow.next_change_at = None
                rainbow.current_step = None

            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

    except Exception as e:
        outcome = "rainbow_change_error"

        logger.exception(
            "[rainbow/change] Error changing rainbow role in guild %s: %s",
            guild.id,
            e,
        )

    if outcome == "rainbow_not_found":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения радужной роли",
                "На этом сервере не настроена радужная роль.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "rainbow_change_error":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка изменения радужной роли",
                "Произошла ошибка при изменении радужной роли. Обратитесь к разработчикам.",  # noqa: E501
            ),
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        view=SuccessViewV2(
            "Изменение радужной роли успешно",
            f"Вы успешно изменили радужную роль на {new_role.mention} ",
        ),
        ephemeral=True,
    )

    item = ChangedRole(
        before_id=before_role_id,  # type: ignore
        after_id=new_role.id,
    )

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.COLOR_UPDATE,
        logging_webhook=logging_webhook,
        moderator_id=interaction.user.id,
        item_name=f"{new_role.mention} ({new_role.id})",
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    logger.info(
        "[command] - invoked guild=%s role_id=%s", guild.id, new_role.id
    )
