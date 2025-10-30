"""Give color to user command."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_or_create_user, get_specified_channel
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.events.dto import (
    AwardNotificationEventDTO,
)
from src.nightcore.features.economy.utils import all_colors_autocomplete
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import (
    ensure_member_exists,
    has_any_role_from_sequence,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@give_group.command(name="color", description="Выдать пользователю цвет.")
@app_commands.describe(
    user="Пользователь, которому выдается цвет.",
    color="Цвет для выдачи.",
)
@app_commands.autocomplete(color=all_colors_autocomplete)
async def give_color(
    interaction: Interaction["Nightcore"],
    user: Member,
    color: str,
):
    """Give a color to user."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    try:
        role_name, role_id, _color = color.split(",")
        role_id = int(role_id)
    except Exception as e:
        logger.error("[give_color] Error parsing color: %s", e)
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи цвета",
                "Не удалось определить цвет.",  # noqa: RUF001
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    member = await ensure_member_exists(guild, user.id)
    if not member:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи цвета",
                "Пользователь не найден на сервере.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    outcome = ""

    if user == bot.user:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи цвета",
                "Невозможно выдать цвет боту.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with specified_guild_config(bot, guild.id, GuildEconomyConfig) as (
        guild_config,
        session,
    ):
        economy_access_roles_ids = guild_config.economy_access_roles_ids

        if not economy_access_roles_ids:
            raise FieldNotConfiguredError("economy access")

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
            user_record, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=user.id,
            )
            drop_from_colors = guild_config.drop_from_colors_case or {}
            color_drop = drop_from_colors.get(_color)

            if not color_drop:
                outcome = "unknown_color"
            else:
                if _color not in user_record.inventory["colors"]:
                    user_record.inventory["colors"].append(_color)
                    attributes.flag_modified(user_record, "inventory")

                    outcome = "success"
                else:
                    outcome = "already_has_color"

    if outcome == "unknown_color":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи цвета",
                "Цвет не был найден.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "already_has_color":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи цвета",
                "У пользователя уже есть этот цвет.",  # noqa: RUF001
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "missing_permissions":
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                "Не удалось выдать цвет пользователю.",  # noqa: RUF001
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Выдача цвета успешна",
                f"Вы успешно выдали пользователю <@{user.id}> цвет <@&{role_id}>.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

        bot.dispatch(
            "user_items_changed",
            dto=AwardNotificationEventDTO(
                guild=guild,
                event_type="give_color",
                logging_channel_id=logging_channel_id,
                user_id=user.id,
                moderator_id=interaction.user.id,
                item_name=f"{role_name} ({role_id})",
                amount=1,
            ),
        )
