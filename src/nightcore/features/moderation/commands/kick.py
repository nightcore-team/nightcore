"""Avatar command for the Nightcore bot."""

import logging
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog
from discord.interactions import Interaction
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.operations import get_moderation_access_roles
from src.nightcore.bot import Nightcore
from src.nightcore.features.moderation.utils import compare_top_roles

logger = logging.getLogger(__name__)


class Kick(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="kick", description="Kick a user from the server"
    )
    async def kick(
        self,
        interaction: Interaction,
        user: discord.User,
        reason: str,
    ):
        """Kick a user from the server."""
        guild = cast(Guild, interaction.guild)
        await interaction.response.defer(thinking=True)

        async with self.bot.uow.start() as uow:
            moderation_access_roles = await get_moderation_access_roles(
                cast(AsyncSession, uow.session), guild_id=guild.id
            )
        has_moder_role = any(
            interaction.user.get_role(role_id)  # type: ignore
            for role_id in moderation_access_roles
        )
        if not has_moder_role:
            await interaction.followup.send(
                "You do not have permission to kick members.",
            )
            return

        if (member := guild.get_member(user.id)) is None:
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
                "You can only kick members from this server.",
            )
            return
        if interaction.user == member:
            await interaction.followup.send(
                "You cannot kick yourself.",
            )
            return

        is_member_moderator = any(
            member.get_role(role_id) for role_id in moderation_access_roles
        )
        if is_member_moderator:
            await interaction.followup.send(
                "You cannot kick moderators.",
            )
            return

        if not guild.me.guild_permissions.kick_members:
            await interaction.followup.send(
                "I do not have permission to kick members.",
            )
            return

        if guild.me == member:
            await interaction.followup.send("You cannot kick me.")
            return

        if not compare_top_roles(guild, member):
            await interaction.followup.send(
                "I cannot kick this user because he has a higher role than me.",  # noqa: E501
            )
            return
        await guild.kick(member, reason=reason)
        await interaction.followup.send(
            "User has been kicked from the server.",
        )


async def setup(bot: Nightcore):
    """Setup the Kick cog."""
    await bot.add_cog(Kick(bot))
