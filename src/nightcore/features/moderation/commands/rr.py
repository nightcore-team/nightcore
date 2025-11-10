"""Rr command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import (
    get_organization_roles_ids,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.components.view import (
    RemoveOrgRoleSelect,
)
from src.nightcore.features.moderation.events import (
    RolesChangeEventData,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import check_required_permissions, PermissionsFlagEnum

logger = logging.getLogger(__name__)


class Rr(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command( # type: ignore
        name="rr",
        description="Удалить организационную роль у пользователя",
    )
    @app_commands.describe(
        user="Пользователь, у которого нужно удалить роль",
    )
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS) # type: ignore
    async def rr(
        self,
        interaction: Interaction,
        user: Member,
    ):
        """Remove organization role from a user."""
        guild = cast(Guild, interaction.guild)

        member = user

        async with self.bot.uow.start() as session:
            if not (
                org_roles_ids := await get_organization_roles_ids(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("organization roles")

        if not guild.me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "У меня нет прав для удаления ролей.",
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете удалить роли у меня.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        # Filter roles that user has
        user_org_roles: list[discord.Role] = [
            r
            for r in (guild.get_role(rid) for rid in org_roles_ids)
            if r and r in member.roles
        ]

        if not user_org_roles:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка снятия роли",
                    "У пользователя нет организационных ролей.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        roles_count = len(user_org_roles)
        logger.info(
            "[command] - user=%s has %d organization roles",
            member.id,
            roles_count,
        )

        if roles_count == 1:
            role = user_org_roles[0]
            await interaction.response.defer(thinking=True)

            try:
                await member.remove_roles(
                    role, reason="Organization role removal via /rr"
                )
            except Exception as e:
                logger.exception("[command] - Failed to remove role: %s", e)
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка снятия роли",
                        "Не удалось снять роль с пользователя.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            try:
                self.bot.dispatch(
                    "roles_change",
                    data=RolesChangeEventData(
                        category="role_remove",
                        moderator=interaction.user,  # type: ignore
                        user=member,
                        role=role,
                        created_at=discord.utils.utcnow().astimezone(
                            tz=timezone.utc
                        ),
                    ),
                    _send_to_rr_channel=True,
                )

            except Exception as e:
                logger.exception(
                    "[event] - Failed to dispatch roles_change event: %s", e
                )
                return

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Роль удалена",
                    f"Роль {role.mention} успешно снята с {member.mention}.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )
        else:
            view = RemoveOrgRoleSelect(
                bot=self.bot,
                member=member,
                roles=user_org_roles,
                moderator=interaction.user,  # type: ignore
                category=self.__class__.__name__.lower(),
            )
            await interaction.response.send_message(
                view=view,
                ephemeral=True,
            )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s",
            interaction.user.id,
            guild.id,
            user.id,
        )


async def setup(bot: "Nightcore"):
    """Setup the Rr cog."""
    await bot.add_cog(Rr(bot))
