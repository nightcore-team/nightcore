"""Fraction Role (/fraction_role) command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import (
    get_fraction_roles_access,
    get_moderation_access_roles,
)
from src.nightcore.bot import Nightcore
from src.nightcore.components import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.events import (
    RolesChangeEventData,
)
from src.nightcore.features.moderation.utils import fraction_roles_autocomplete
from src.nightcore.utils import ensure_member_exists

logger = logging.getLogger(__name__)

# TODO: logs about user's roles changing


class FractionRole(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="fraction_role", description="Assigns a fraction role to a user."
    )
    @app_commands.describe(
        user="The user to assign the role to.",
        role="The role to assign.",
        option="An optional parameter.",
    )
    @app_commands.choices(
        option=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
        ]
    )
    @app_commands.autocomplete(role=fraction_roles_autocomplete)
    async def fraction_role(
        self,
        interaction: Interaction,
        user: discord.User,
        role: str,
        option: str,
    ) -> None:
        """Assigns a fraction role to a user."""
        guild = cast(Guild, interaction.guild)
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Ensure we have a guild Member object
        member = await ensure_member_exists(guild, user)

        if member is None:
            return await interaction.followup.send(
                embed=EntityNotFoundEmbed(
                    "user",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            role_id = int(role)
        except ValueError:
            return await interaction.followup.send(
                embed=ValidationErrorEmbed(
                    "Invalid role ID (not an integer).",
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
                fraction_roles_access_roles := await get_fraction_roles_access(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("fraction roles access")

            final_access_list = (
                moderation_access_roles + fraction_roles_access_roles
            )

        has_moder_role = any(
            interaction.user.get_role(role_id)  # type: ignore
            for role_id in final_access_list
        )
        if not has_moder_role:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        target_role = guild.get_role(role_id)

        if target_role is None:
            return await interaction.followup.send(
                embed=EntityNotFoundEmbed(
                    "role",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        member_roles = {r.id for r in member.roles}
        has_role = role_id in member_roles

        match option:
            case "add":
                if not has_role:
                    try:
                        await member.add_roles(target_role)
                    except Exception as e:
                        logger.exception("Failed to add role: %s", e)
                        return await interaction.followup.send(
                            embed=ErrorEmbed(
                                "Role Assignment Failed",
                                "Failed to add role.",
                                self.bot.user.name,  # type: ignore
                                self.bot.user.display_avatar.url,  # type: ignore
                            ),
                            ephemeral=True,
                        )
                    await interaction.followup.send(
                        embed=SuccessMoveEmbed(
                            "Role Assignment Successful",
                            f"Added {target_role.mention} to {member.mention}'s fraction roles.",  # noqa: E501
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                else:
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "Role Assignment Failed",
                            f"{member.mention} already has {target_role.mention}.",  # noqa: E501
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
            case "remove":
                if has_role:
                    try:
                        await member.remove_roles(target_role)
                    except Exception as e:
                        logger.exception("Failed to remove role: %s", e)
                        return await interaction.followup.send(
                            embed=ErrorEmbed(
                                "Role Removal Failed",
                                f"Failed to remove {target_role.mention} from {member.mention}'s fraction roles.",  # noqa: E501
                                self.bot.user.name,  # type: ignore
                                self.bot.user.display_avatar.url,  # type: ignore
                            ),
                            ephemeral=True,
                        )
                    await interaction.followup.send(
                        embed=SuccessMoveEmbed(
                            "Role Removal Successful",
                            f"Removed {target_role.mention} from {member.mention}'s fraction roles.",  # noqa: E501
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                else:
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "Role Removal Failed",
                            f"{member.mention} does not have {target_role.mention}.",  # noqa: E501
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
            case _:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Invalid Option",
                        "Option must be 'add' or 'remove'.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

        try:
            self.bot.dispatch(
                "roles_change",
                data=RolesChangeEventData(
                    category=f"fraction_role_{option}",
                    moderator=interaction.user,  # type: ignore
                    user=member,
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
            return

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s option=%s role=%s",
            interaction.user.id,
            guild.id,
            member.id,
            option,
            role_id,
        )


async def setup(bot: Nightcore):
    """Setup the FractionRole Cog."""
    await bot.add_cog(FractionRole(bot))
