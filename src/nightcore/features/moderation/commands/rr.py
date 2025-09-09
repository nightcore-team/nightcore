"""Rr command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import (
    get_moderation_access_roles,
    get_organization_roles_ids,
)
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
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
from src.nightcore.utils import ensure_member_exists

logger = logging.getLogger(__name__)


class Rr(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="rr", description="Remove organization role from a user"
    )
    @app_commands.describe(
        user="The user to remove the role from",
    )
    async def rr(
        self,
        interaction: Interaction,
        user: discord.User,
    ):
        """Remove organization role from a user."""
        guild = cast(Guild, interaction.guild)

        # Ensure we have a guild Member object
        member = await ensure_member_exists(guild, user)

        if member is None:
            return await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "user",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        async with self.bot.uow.start() as session:
            if not (
                moderation_access_roles := await get_moderation_access_roles(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("moderation access")

            if not (
                org_roles_ids := await get_organization_roles_ids(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("organization roles")

        has_moder_role = any(
            interaction.user.get_role(role_id)  # type: ignore
            for role_id in moderation_access_roles
        )
        if not has_moder_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not guild.me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to remove roles.",
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot remove roles from me.",
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
                embed=ValidationErrorEmbed(
                    "User has no organization roles.",
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
                        "Role Removal Failed",
                        "Failed to remove role.",
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
                    "Role Removed",
                    f"Successfully removed role {role.mention} from {member.mention}.",  # noqa: E501
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


async def setup(bot: Nightcore):
    """Setup the Rr cog."""
    await bot.add_cog(Rr(bot))
