"""Command to apply a color role to yourself."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, Role, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_or_create_user
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.economy.utils import (
    CLEAR_COLOR_ID,
    user_colors_autocomplete,
)
from src.nightcore.services.config import specified_guild_config

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
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    @app_commands.guild_only()
    async def paint(
        self,
        interaction: Interaction["Nightcore"],
        color_name: str,
    ):
        """Apply a color role to the user or reset all color roles."""

        guild = cast(Guild, interaction.guild)
        member = cast(Member, interaction.user)

        try:
            color_id = int(color_name)
        except Exception as _:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка",
                    "Был введен неверный id цвета",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""

        async with specified_guild_config(
            self.bot, guild.id, GuildEconomyConfig
        ) as (_, session):
            user_record, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=member.id,
            )

            if color_id == CLEAR_COLOR_ID:
                color_roles_to_remove = []

                # TODO: ЗДЕСЬ ДОЛЖНА БЫТЬ ПРОВЕРКА HA BCE ЦВЕТА ГИЛЬДИИ,
                # A HE ТОЛЬКО HA TE, КОТОРЫЕ СЕЙЧАС ECTb Y ЮЗЕРА

                for user_color in user_record.colors:
                    color_role = guild.get_role(user_color.role_id)
                    if color_role and color_role in member.roles:
                        color_roles_to_remove.append(color_role)

                if not color_roles_to_remove:
                    outcome = "no_color_to_reset"
                else:
                    try:
                        await member.remove_roles(
                            *color_roles_to_remove,
                            reason="User reset their color.",
                        )
                        outcome = "reset_success"
                    except discord.Forbidden:
                        outcome = "no_permissions"
                    except discord.HTTPException as e:
                        logger.exception(
                            "[paint] Error removing color roles from user %s in guild %s: %s",  # noqa: E501
                            member.id,
                            guild.id,
                            e,
                        )
                        outcome = "error"

            else:
                if (selected_color := user_record.get_color(color_id)) is None:
                    outcome = "color_not_owned"

                else:
                    role = guild.get_role(selected_color.role_id)
                    if role is None:
                        outcome = "role_not_found"
                    elif role in member.roles:
                        outcome = "already_has_role"
                    else:
                        # TODO: ЗДЕСЬ ДОЛЖНА БЫТЬ ПРОВЕРКА HA BCE ЦВЕТА ГИЛЬДИИ
                        # A HE ТОЛЬКО HA TE, КОТОРЫЕ СЕЙЧАС ECTb Y ЮЗЕРА

                        color_roles_to_remove: list[Role] = []
                        for user_color in user_record.colors:
                            if user_color.id == selected_color.id:
                                continue

                            other_color_data = drop_from_colors.get(
                                user_color_key
                            )
                            if other_color_data:
                                other_color_role = guild.get_role(
                                    other_color_data["role_id"]
                                )
                                if (
                                    other_color_role
                                    and other_color_role in member.roles
                                ):
                                    color_roles_to_remove.append(
                                        other_color_role
                                    )

                        try:
                            if color_roles_to_remove:
                                await member.remove_roles(
                                    *color_roles_to_remove,
                                    reason="User changed their color.",
                                )

                            await member.add_roles(
                                role, reason="User painted themselves."
                            )
                            outcome = "success"

                        except discord.Forbidden:
                            outcome = "no_permissions"
                        except discord.HTTPException as e:
                            logger.exception(
                                "[paint] Error applying color role to user %s in guild %s: %s",  # noqa: E501
                                member.id,
                                guild.id,
                                e,
                            )
                            outcome = "error"

        if outcome == "no_color_to_reset":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка сброса цвета",
                    "У вас нет активного цвета для сброса.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "reset_success":
            return await interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Сброс цвета",
                    "Вы успешно сбросили свой цвет.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "color_not_owned":
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
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "already_has_role":
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
                    "Цвет применен",
                    f"Вы успешно применили цвет {role.mention}.",  # type: ignore
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        logger.info(
            "[command] - invoked user=%s guild=%s color_id=%s",
            member.id,
            guild.id,
            role.id,  # type: ignore
            color_id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Paint cog."""
    await bot.add_cog(Paint(bot))
