"""Command to create rainbow role."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.interactions import Interaction
from sqlalchemy.exc import IntegrityError

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models.rainbow import RainbowRole
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


@rainbow_group.command(name="create", description="Создать радужную роль")  # type: ignore
@app_commands.describe(change_type="Тип смены цвета радужной роли")
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
async def create_rainbow(
    interaction: Interaction["Nightcore"],
    role: discord.Role,
    change_type: str = RainbowColorChangeTypeEnum.OFFSET.value,
):
    """Create rainbow role."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    logging_webhook = None
    outcome = ""

    if role.position >= member.top_role.position:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка создания радужной роли",
                "Вы не можете использовать роль с позицией выше чем ваша высшая роль.",  # noqa: E501
            ),
            ephemeral=True,
        )
        return

    if role.permissions.administrator:
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка создания радужной роли",
                "Радужная роль не может иметь права администратора.",
            ),
            ephemeral=True,
        )
        return

    if not compare_top_roles(guild, role):
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка создания радужной роли",
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

            if rainbow is not None:
                outcome = "rainbow_exists"
            else:
                new_rainbow = RainbowRole(
                    guild_id=guild.id,
                    role_id=role.id,
                    change_type=RainbowColorChangeTypeEnum(change_type),
                )

                session.add(new_rainbow)

                logging_webhook = await get_specified_webhook(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_ECONOMY,
                )

    except IntegrityError:
        outcome = "rainbow_exists"

        logger.warning(
            "[rainbow/create] Error creating rainbow role in guild %s with existing role %s",  # noqa: E501
            guild.id,
            role.id,
        )

    except Exception as e:
        outcome = "rainbow_create_error"

        logger.exception(
            "[rainbow/create] Error creating rainbow role in guild %s: %s",
            guild.id,
            e,
        )

    if outcome == "rainbow_exists":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка создания радужной роли",
                "На этом сервере уже настроена радужная роль. Используйте команду `/rainbow change` для изменения роли.",  # noqa: E501
            ),
            ephemeral=True,
        )
        return

    if outcome == "rainbow_create_error":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка создания радужной роли",
                "Произошла ошибка при создании радужной роли.",
            ),
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        view=SuccessViewV2(
            "Создание радужной роли успешно",
            f"Вы успешно настроили радужную роль {role.mention} ",
        ),
        ephemeral=True,
    )

    item = ChangedRole(after_id=role.id)

    dto = ItemChangeNotifyEventDTO(
        guild=guild,
        event_type=ItemChangeActionEnum.CREATE.value,
        logging_webhook=logging_webhook,
        moderator_id=interaction.user.id,
        item_name=f"{role.mention} ({role.id})",
        item=item,
    )

    bot.dispatch("item_change_notify", dto)

    logger.info("[command] - invoked guild=%s role_id=%s", guild.id, role.id)
