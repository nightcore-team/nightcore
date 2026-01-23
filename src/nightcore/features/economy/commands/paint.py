"""Command to apply a color role to yourself."""

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, Role, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models.color import Color
from src.infra.db.models.user import User
from src.infra.db.operations import get_guild_colors, get_or_create_user
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.economy.utils import (
    CLEAR_COLOR_ID,
    user_colors_autocomplete,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class Paint(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(name="paint", description="Применить на себя цвет")  # type: ignore
    @app_commands.autocomplete(color=user_colors_autocomplete)
    @app_commands.describe(color="Цвет, который вы хотите применить")
    @app_commands.rename(color_id="color")
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    @app_commands.guild_only()
    async def paint(
        self,
        interaction: Interaction["Nightcore"],
        color_id: app_commands.Transform[int, StrToIntTransformer],
    ):
        """Apply a color role to the user or reset all color roles."""

        bot = self.bot
        guild = cast(Guild, interaction.guild)
        member = cast(Member, interaction.user)

        outcome = ""

        async with bot.uow.start() as session:
            user_record, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=member.id,
                with_relations=True,
            )

            guild_colors = await get_guild_colors(session, guild_id=guild.id)

        if color_id == CLEAR_COLOR_ID:
            outcome = await _reset_color_command(guild, member, guild_colors)

            success_description = "Вы успешно сбросили свой цвет."
        else:
            outcome, role = await _choose_color(
                guild, user_record, member, guild_colors, color_id
            )

            if role is not None:
                success_description = (
                    f"Вы успешно применили цвет {role.mention}."
                )

        if outcome == "already_have_color":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка выдачи цвета",
                    "Вы уже применили на себя этот цвет.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "no_permissions":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка выдачи цвета",
                    "У бота нет прав для управления ролями.\n"
                    "Обратитесь к администрации.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "no_colors_to_reset":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка сброса цвета",
                    "У вас нет активного цвета для сброса.",
                    interaction.client.user.display_name,  # type: ignore
                    interaction.client.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "no_color_in_inventory":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка выдачи цвета",
                    "У вас нет этого цвета в инвентаре.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "role_not_found":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка выдачи цвета",
                    "Роль цвета не найдена на сервере.",
                    interaction.client.user.display_name,  # type: ignore
                    interaction.client.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "error":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка выдачи цвета",
                    "Произошла ошибка при применении цвета",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            await interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Изменение цвета",
                    success_description,  # type: ignore
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        logger.info(
            "[command] - invoked user=%s guild=%s color_id=%s",
            member.id,
            guild.id,
            color_id,
            color_id,
        )


async def _reset_color_command(
    guild: Guild,
    member: Member,
    guild_colors: Sequence[Color],
) -> str:
    color_roles_to_remove: list[Role] = []

    for guild_color in guild_colors:
        color_role = guild.get_role(guild_color.role_id)
        if color_role and color_role in member.roles:
            color_roles_to_remove.append(color_role)

    if len(color_roles_to_remove) < 1:
        return "no_colors_to_reset"

    try:
        await member.remove_roles(
            *color_roles_to_remove, atomic=True, reason="/paint"
        )

    except discord.Forbidden:
        return "no_permissions"
    except discord.HTTPException as e:
        logger.exception(
            "[paint] Error applying color role to user %s in guild %s: %s",
            member.id,
            guild.id,
            e,
        )

        return "error"

    return "success"


async def _choose_color(
    guild: Guild,
    user_record: User,
    member: Member,
    guild_colors: Sequence[Color],
    color_id: int,
) -> tuple[str, Role | None]:
    if (selected_color := user_record.get_color(color_id)) is None:
        return "no_color_in_inventory", None

    color_roles_to_remove: list[Role] = []
    new_roles: list[Role] = member.roles[1:]

    for guild_color in guild_colors:
        color_role = guild.get_role(guild_color.role_id)
        if color_role and color_role in member.roles:
            color_roles_to_remove.append(color_role)

    role = guild.get_role(selected_color.role_id)

    if role is None:
        return "role_not_found", None

    if role in member.roles:
        return "already_have_color", None

    try:
        if color_roles_to_remove:
            new_roles.remove(*color_roles_to_remove)

        new_roles.append(role)

        await member.edit(roles=new_roles, reason="/paint")

    except discord.Forbidden:
        return "no_permissions", None
    except discord.HTTPException as e:
        logger.exception(
            "[paint] Error applying color role to user %s in guild %s: %s",
            member.id,
            guild.id,
            e,
        )

        return "error", None

    return "success", role


async def setup(bot: "Nightcore") -> None:
    """Setup the Paint cog."""
    await bot.add_cog(Paint(bot))
