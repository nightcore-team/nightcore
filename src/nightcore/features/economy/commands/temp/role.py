"""Command to give a role to a user for a limited time."""

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, Role, app_commands
from discord.interactions import Interaction

from src.infra.db.models import (
    GuildEconomyConfig,
    GuildLoggingConfig,
    TempRole,
)
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    get_specified_channel,
    get_specified_field,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.economy._groups import temp as temp_group
from src.nightcore.features.economy.events.dto import (
    AwardNotificationEventDTO,
)
from src.nightcore.utils import compare_top_roles, has_any_role_from_sequence
from src.nightcore.utils.time_utils import parse_duration

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@temp_group.command(name="role", description="Выдать пользователю роль")
@app_commands.describe(
    user="Пользователь, которому выдается роль.",
    role="Роль для выдачи.",
    duration="Срок действия роли.",
)
async def give_role(
    interaction: Interaction["Nightcore"],
    user: Member,
    role: Role,
    duration: str,
):
    """Give a role to user for a limited time."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    outcome = ""

    if user == bot.user:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи роли",
                "Невозможно выдать временную роль боту.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if not compare_top_roles(guild, role):
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
                "Я не могу выдать временную роль человеку, которая выше моей.",
            ),
            ephemeral=True,
        )

    parsed_duration = parse_duration(duration)

    if not parsed_duration:
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "Неверная продолжительность. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                bot.user.name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with bot.uow.start() as session:
        economy_access_roles_ids = await get_specified_field(
            session,
            guild_id=guild.id,
            config_type=GuildEconomyConfig,
            field_name="economy_access_roles_ids",
        )

        if not economy_access_roles_ids:
            raise FieldNotConfiguredError("доступ к экономике")

        if not has_any_role_from_sequence(
            cast(Member, interaction.user), economy_access_roles_ids
        ):
            outcome = "missing_permissions"

        logging_channel_id = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_ECONOMY,
        )

        if not outcome:
            outcome = "success"

    if outcome == "missing_permissions":
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        try:
            async with bot.uow.start() as session:
                temp_role = TempRole(
                    guild_id=guild.id,
                    user_id=user.id,
                    role_id=role.id,
                    duration=parsed_duration,
                    end_time=datetime.now(timezone.utc)
                    + timedelta(seconds=parsed_duration),
                )
                session.add(temp_role)

        except Exception as e:
            logger.exception(
                "[temp/role] Failed to create temporary role record %s to user %s in guild %s: %s",  # noqa: E501
                role.id,
                user.id,
                guild.id,
                e,
            )
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка выдачи временной роли",
                    "Не удалось выдать временную роль пользователю.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
        try:
            await user.add_roles(
                role, reason="Temporary role assigned via economy command."
            )
        except Exception as e:
            logger.exception(
                "[temp/role] Failed to assign role %s to user %s in guild %s: %s",  # noqa: E501
                role.id,
                user.id,
                guild.id,
                e,
            )
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка выдачи временной роли",
                    "Не удалось выдать временную роль пользователю.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Временная роль выдана",
                f"Вы успешно выдали пользователю {user.mention} "
                f"роль {role.mention} на срок {duration}.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

        logger.info(
            "[command] - invoker user=%s guild=%s selected_user=%s role=%s duration=%s",  # noqa: E501
            interaction.user.id,
            guild.id,
            user.id,
            role.id,
            duration,
        )

        bot.dispatch(
            "user_items_changed",
            dto=AwardNotificationEventDTO(
                guild=guild,
                event_type="temp/role",
                logging_channel_id=logging_channel_id,
                user_id=user.id,
                moderator_id=interaction.user.id,
                item_name=f"временная роль (`{role.id}`)",
                amount=1,
            ),
        )
