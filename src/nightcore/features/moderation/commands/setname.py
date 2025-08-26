"""Setname command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import get_moderation_access_roles
from src.nightcore.bot import Nightcore
from src.nightcore.components import (
    EntityNotFoundEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.moderation.events import (
    UserPunishmentEventData,
)
from src.nightcore.features.moderation.utils import (
    compare_top_roles,
)
from src.nightcore.utils import ensure_member_exists

logger = logging.getLogger(__name__)


class Setname(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="setname", description="Set/restore a user's nickname"
    )
    @app_commands.describe(
        user="The user to set/restore the nickname for",
        reason="The reason for changing the nickname",
    )
    async def setname(
        self,
        interaction: Interaction,
        user: discord.User | discord.Member,
        reason: str,
        nickname: str | None = None,
    ):
        """Set/restore a user's nickname."""
        guild = cast(Guild, interaction.guild)

        # check moderation access
        async with self.bot.uow.start() as session:
            moderation_access_roles = await get_moderation_access_roles(
                session, guild_id=guild.id
            )
        has_moder_role = any(
            interaction.user.get_role(role_id)  # type: ignore
            for role_id in moderation_access_roles
        )
        if not has_moder_role:
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        # Ensure we have a guild Member object
        member = await ensure_member_exists(guild, user)

        if member is None:
            await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "user",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        is_member_moderator = any(
            member.get_role(role_id) for role_id in moderation_access_roles
        )
        if is_member_moderator:
            await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You can't set/restore a moderator's nickname.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        if not guild.me.guild_permissions.change_nickname:
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to change nicknames.",
                ),
                ephemeral=True,
            )
            return

        if guild.me == member:
            await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "You cannot change my nickname.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            return

        if not compare_top_roles(guild, member):
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I cannot change this user's nickname because he has a higher role than me.",  # noqa: E501
                ),
                ephemeral=True,
            )
            return

        old_member_nickname = member.display_name

        if nickname:
            if len(nickname) > 32:
                await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        "The nickname cannot be longer than 32 characters.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                return
        else:
            nickname = member.global_name

        await interaction.response.defer(thinking=True)

        try:
            await member.edit(nick=nickname)
        except Exception as e:
            logger.exception("[command] - Failed to set user nickname: %s", e)
            return

        try:
            self.bot.dispatch(
                "user_punish",
                data=UserPunishmentEventData(
                    moderator=interaction.user,  # type: ignore
                    user=member,
                    category=self.__class__.__name__.lower(),
                    reason=reason,
                    send_dm=False,
                    old_nickname=old_member_nickname,
                    new_nickname=nickname,
                    created_at=discord.utils.utcnow().astimezone(timezone.utc),
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_punish event: %s", e
            )

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "Nickname Changed",
                f"Successfully changed {member.mention}'s nickname.",
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            )
        )


async def setup(bot: Nightcore):
    """Setup the Setname cog."""
    await bot.add_cog(Setname(bot))
