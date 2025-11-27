"""Command to add fraction role to a user."""

import logging
from datetime import timezone
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildModerationConfig
from src.infra.db.operations import (
    get_specified_field,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.events import (
    RolesChangeEventData,
)
from src.nightcore.features.moderation.utils import fraction_roles_autocomplete
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import (
    ensure_role_exists,
    has_any_role,
    has_any_role_from_sequence,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class FractionRole(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="fraction_role",
        description="Выдать пользователю фракционную роль.",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        user="Пользователь, которому нужно выдать роль.",
        role="Роль, которую нужно выдать.",
        option="Выдать или снять.",
    )
    @app_commands.choices(
        option=[
            app_commands.Choice(name="Добавить", value="add"),
            app_commands.Choice(name="Удалить", value="remove"),
        ]
    )
    @app_commands.autocomplete(role=fraction_roles_autocomplete)
    @check_required_permissions(PermissionsFlagEnum.UNSAFE)  # type: ignore
    async def fraction_role(
        self,
        interaction: Interaction,
        user: Member,
        role: str,
        option: str,
    ) -> None:
        """Assigns a fraction role to a user."""

        guild = cast(Guild, interaction.guild)
        author = cast(Member, interaction.user)

        await interaction.response.defer(ephemeral=True, thinking=True)

        if not guild.me.guild_permissions.manage_roles:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "У меня нет прав для выдачи ролей пользователям.",
                ),
            )

        async with specified_guild_config(
            self.bot, guild.id, GuildModerationConfig
        ) as (moderation_config, session):
            # Moderation access roles
            moderation_access_roles = (
                moderation_config.moderation_access_roles_ids
            )
            if not moderation_access_roles:
                raise FieldNotConfiguredError("доступ к модерации")

            # Fraction roles config (dict: role_id -> [access_role_ids])
            fraction_roles: dict[str, list[int]] = await get_specified_field(
                session,
                guild_id=guild.id,
                config_type=GuildModerationConfig,
                field_name="fraction_roles_access_roles_ids",
            )

        if role not in fraction_roles:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка выдачи роли",
                    "Роль не найдена в списке фракционных ролей.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )

        has_access = has_any_role_from_sequence(
            author, moderation_access_roles + fraction_roles.get(role, [])
        )

        if not has_access:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
            )

        target_role = await ensure_role_exists(guild, int(role))

        if target_role is None:
            return await interaction.followup.send(
                embed=EntityNotFoundEmbed(
                    "фракционная роль",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
            )

        has_role = has_any_role(user, target_role.id)

        match option:
            case "add":
                if has_role:
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "Ошибка выдачи роли",
                            f"{user.mention} уже имеет роль {target_role.mention}.",  # noqa: E501
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                    )

                try:
                    await user.add_roles(target_role)
                except Exception as e:
                    logger.exception("Failed to add role: %s", e)
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "Ошибка выдачи роли",
                            "Не удалось выдать роль пользователю.",
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                    )

                await interaction.followup.send(
                    embed=SuccessMoveEmbed(
                        "Выдача роли",
                        f"Роль {target_role.mention} была выдана пользователю {user.mention}.",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            case "remove":
                if not has_role:
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "Ошибка снятия роли",
                            f"{user.mention} не имеет роль {target_role.mention}.",  # noqa: E501
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                    )

                try:
                    await user.remove_roles(target_role)
                except Exception as e:
                    logger.exception("Failed to remove role: %s", e)
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "Ошибка снятия роли",
                            f"Не удалось снять {target_role.mention} у {user.mention}.",  # noqa: E501
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                    )

                await interaction.followup.send(
                    embed=SuccessMoveEmbed(
                        "Снятие роли",
                        f"Роль {target_role.mention} была снята у пользователя {user.mention}.",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            case _:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Недопустимый вариант",
                        "Вариант должен быть 'Добавить' или 'Удалить'.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

        try:
            self.bot.dispatch(
                "roles_change",
                data=RolesChangeEventData(
                    category=f"fraction_role_{option}",
                    moderator=author,
                    user=user,
                    role=target_role,
                    created_at=discord.utils.utcnow().astimezone(
                        tz=timezone.utc
                    ),
                ),
                _create_punish=False,
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch roles_change event: %s", e
            )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s option=%s role=%s",
            author.id,
            guild.id,
            user.id,
            option,
            role,
        )


async def setup(bot: "Nightcore"):
    """Setup the FractionRole Cog."""
    await bot.add_cog(FractionRole(bot))
