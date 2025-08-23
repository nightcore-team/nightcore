"""Fraction Role (/fraction_role) command for the Nightcore bot."""

import logging
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.operations import (
    get_fraction_roles_access,
    get_moderation_access_roles,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.utils import fraction_roles_autocomplete

logger = logging.getLogger(__name__)

# TODO: add embed as a returning and implement sending
# logs about user's roles changing

# TODO: ensure_member_exists util for checking if user is in the guild


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
        user: discord.Member | discord.User,
        role: str,
        option: str,
    ) -> None:
        """Assigns a fraction role to a user."""
        guild = cast(Guild, interaction.guild)
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            role_id = int(role)
        except ValueError:
            await interaction.followup.send(
                "Invalid role ID (not an integer)."
            )
            return

        async with self.bot.uow.start() as uow:
            moderation_access_roles = await get_moderation_access_roles(
                cast(AsyncSession, uow.session), guild_id=guild.id
            )

            fraction_roles_access_roles = await get_fraction_roles_access(
                cast(AsyncSession, uow.session), guild_id=guild.id
            )

            final_access_list = (
                moderation_access_roles + fraction_roles_access_roles
            )

        has_moder_role = any(
            interaction.user.get_role(role_id)  # type: ignore
            for role_id in final_access_list
        )
        if not has_moder_role:
            await interaction.followup.send(
                "You do not have permission to add fraction roles to members.",
            )
            return

        # Ensure we have a guild Member object
        member: discord.Member

        if isinstance(user, discord.Member):
            member = user
        else:
            try:
                member = await guild.fetch_member(user.id)
            except discord.NotFound:
                await interaction.followup.send(
                    "User not found on the server!",
                )
                return
            except Exception as e:
                logger.exception("fetch_member failed: %s", e)
                await interaction.followup.send(
                    "Error fetching user information.",
                )
                return
            await interaction.followup.send(
                "You can only add roles to members from this server.",
            )
            return

        target_role = guild.get_role(role_id)

        if target_role is None:
            await interaction.followup.send("Role not found in this guild.")
            return

        member_roles = {r.id for r in member.roles}
        has_role = role_id in member_roles

        match option:
            case "add":
                if not has_role:
                    try:
                        await member.add_roles(target_role)
                    except Exception as e:
                        logger.exception("Failed to add role: %s", e)
                        await interaction.followup.send("Failed to add role.")
                        return
                    await interaction.followup.send(
                        f"Added {target_role.mention} to {member.mention}'s fraction roles."  # noqa: E501
                    )
                    return
                await interaction.followup.send(
                    f"{member.mention} already has {target_role.mention}."
                )
            case "remove":
                if has_role:
                    try:
                        await member.remove_roles(target_role)
                    except Exception as e:
                        logger.exception("Failed to remove role: %s", e)
                        await interaction.followup.send(
                            "Failed to remove role."
                        )
                        return
                    await interaction.followup.send(
                        f"Removed {target_role.mention} from {member.mention}'s fraction roles."  # noqa: E501
                    )
                    return
                await interaction.followup.send(
                    f"{member.mention} does not have {target_role.mention}."
                )
            case _:
                await interaction.followup.send("Unknown option.")


async def setup(bot: Nightcore):
    """Setup the FractionRole Cog."""
    await bot.add_cog(FractionRole(bot))
