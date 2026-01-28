"""Command to give color to a user."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    get_color_by_id,
    get_or_create_user,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.events.dto import (
    AwardNotificationEventDTO,
)
from src.nightcore.features.economy.utils import guild_colors_autocomplete
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@give_group.command(name="color", description="Выдать пользователю цвет")  # type: ignore
@app_commands.describe(
    user="Пользователь, которому выдается цвет",
    color_id="Цвет для выдачи",
    reason="Причина выдачи цвета (необязательно)",
)
@app_commands.autocomplete(color_id=guild_colors_autocomplete)
@app_commands.rename(color_id="color")
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def give_color(
    interaction: Interaction["Nightcore"],
    user: User,
    color_id: app_commands.Transform[int, StrToIntTransformer],
    reason: str | None = None,
):
    """Give a color to user."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

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

    async with bot.uow.start() as session:
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
                with_relations=True,
            )
            color = await get_color_by_id(
                session, guild_id=guild.id, color_id=color_id
            )

            if color is None:
                outcome = "unknown_color"
            else:
                if color not in user_record.colors:
                    user_record.colors.append(color)

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
                "У пользователя уже есть этот цвет.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Выдача цвета успешна",
                f"Вы успешно выдали пользователю <@{user.id}> цвет <@&{color.role_id}>.",  # noqa: E501 # type: ignore
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

        color_role = guild.get_role(color.role_id)  # type: ignore

        color_name = color_role.name if color_role else "unknown"

        bot.dispatch(
            "user_items_changed",
            dto=AwardNotificationEventDTO(
                guild=guild,
                event_type="give/color",
                logging_channel_id=logging_channel_id,
                user_id=user.id,
                moderator_id=interaction.user.id,
                item_name=f"{color_name} ({color.role_id})",  # type: ignore
                amount=1,
                reason=reason,
            ),
        )
