"""Command to add fraction role to a user."""

import logging
from datetime import UTC
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildModerationConfig

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.view.v2 import (
    EntityNotFoundViewV2,
    ErrorViewV2,
    MissingPermissionsViewV2,
    SuccessViewV2,
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
        name="give_role",
        description="Выдать пользователю роль.",
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
    async def give_role(
        self,
        interaction: Interaction,
        user: Member,
        role: str,
        option: str,
    ) -> None:
        """Assigns a fraction role to a user."""

        try:
            role_id = int(role)
        except ValueError:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка выдачи роли",
                    "Выбранная роль не найдена.",
                ),
                ephemeral=True,
            )
            return

        guild = cast(Guild, interaction.guild)
        author = cast(Member, interaction.user)

        await interaction.response.defer(ephemeral=True, thinking=True)

        if not guild.me.guild_permissions.manage_roles:
            await interaction.followup.send(
                view=MissingPermissionsViewV2(
                    "У меня нет прав для выдачи ролей пользователям.",
                ),
            )
            return

        async with specified_guild_config(
            self.bot, guild.id, GuildModerationConfig
        ) as (moderation_config, _):
            # Moderation access roles
            moderation_access_roles = (
                moderation_config.moderation_access_roles_ids
            )
            if not moderation_access_roles:
                raise FieldNotConfiguredError("доступ к модерации")

            fraction_roles = moderation_config.fraction_roles_access_roles_ids

        if not any(role_id == item.role_id for item in fraction_roles):
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка выдачи роли",
                    "Роль не найдена в списке для выдачи.",
                )
            )
            return

        access_roles: list[int] = []

        for item in fraction_roles:
            if item.role_id == role_id:
                access_roles = item.access_roles

        has_access = has_any_role_from_sequence(
            author, moderation_access_roles + access_roles
        )

        if not has_access:
            await interaction.followup.send(
                view=MissingPermissionsViewV2(),
            )
            return

        target_role = await ensure_role_exists(guild, role_id)

        if target_role is None:
            await interaction.followup.send(
                view=EntityNotFoundViewV2("фракционная роль"),
            )
            return

        has_role = has_any_role(user, target_role.id)

        match option:
            case "add":
                if has_role:
                    await interaction.followup.send(
                        view=ErrorViewV2(
                            "Ошибка выдачи роли",
                            f"{user.mention} уже имеет роль {target_role.mention}.",  # noqa: E501
                        ),
                    )
                    return

                try:
                    await user.add_roles(target_role)
                except Exception as e:
                    logger.exception("Failed to add role: %s", e)
                    await interaction.followup.send(
                        view=ErrorViewV2(
                            "Ошибка выдачи роли",
                            "Не удалось выдать роль пользователю.",
                        ),
                    )
                    return

                await interaction.followup.send(
                    view=SuccessViewV2(
                        "Выдача роли",
                        f"Роль {target_role.mention} была выдана пользователю {user.mention}.",  # noqa: E501
                    ),
                )

            case "remove":
                if not has_role:
                    await interaction.followup.send(
                        view=ErrorViewV2(
                            "Ошибка снятия роли",
                            f"{user.mention} не имеет роль {target_role.mention}.",  # noqa: E501
                        ),
                    )
                    return

                try:
                    await user.remove_roles(target_role)
                except Exception as e:
                    logger.exception("Failed to remove role: %s", e)
                    await interaction.followup.send(
                        view=ErrorViewV2(
                            "Ошибка снятия роли",
                            f"Не удалось снять {target_role.mention} у {user.mention}.",  # noqa: E501
                        ),
                    )
                    return

                await interaction.followup.send(
                    view=SuccessViewV2(
                        "Снятие роли",
                        f"Роль {target_role.mention} была снята у пользователя {user.mention}.",  # noqa: E501
                    ),
                )

            case _:
                await interaction.followup.send(
                    view=ErrorViewV2(
                        "Недопустимый вариант",
                        "Вариант должен быть 'Добавить' или 'Удалить'.",
                    ),
                )
                return

        try:
            self.bot.dispatch(
                "roles_change",
                data=RolesChangeEventData(
                    category=f"fraction_role_{option}",
                    moderator=author,
                    user=user,
                    roles_ids=[target_role.id],
                    created_at=discord.utils.utcnow().astimezone(tz=UTC),
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
