"""Kick command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import get_moderation_access_roles
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.events import UserKickEventData
from src.nightcore.utils import (
    compare_top_roles,
    ensure_member_exists,
    has_any_role_from_sequence,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Kick(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(
        name="kick",
        description="Кикнуть пользователя с сервера",
    )
    @app_commands.describe(user="Пользователь для кика", reason="Причина кика")
    async def kick(
        self,
        interaction: Interaction,
        user: discord.User,
        reason: str,
    ):
        """Kick a user from the server."""
        guild = cast(Guild, interaction.guild)

        # Ensure we have a guild Member object
        member = await ensure_member_exists(guild, user.id)

        if member is None:
            return await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "пользователь",
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
                raise FieldNotConfiguredError("доступ к модерации")

        has_moder_role = has_any_role_from_sequence(
            cast(discord.Member, interaction.user), moderation_access_roles
        )
        if not has_moder_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        is_member_moderator = has_any_role_from_sequence(
            member, moderation_access_roles
        )
        if is_member_moderator:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете кикнуть модераторов.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if member.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете заблокировать администраторов.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not guild.me.guild_permissions.kick_members:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "У меня нет прав для кика участников.",
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете кикнуть меня.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not compare_top_roles(guild, member):
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "Я не могу кикнуть этого пользователя, потому что у него роль выше моей.",  # noqa: E501
                ),
                ephemeral=True,
            )

        try:
            self.bot.dispatch(
                "user_kicked",
                data=UserKickEventData(
                    moderator=interaction.user,  # type: ignore
                    user=member,
                    category=self.__class__.__name__.lower(),
                    reason=reason,
                    created_at=discord.utils.utcnow().astimezone(
                        tz=timezone.utc
                    ),
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_kicked event: %s", e
            )
            return

        try:
            await guild.kick(member, reason=reason)
        except Exception as e:
            logger.exception("[command] - Failed to kick user: %s", e)
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка кика",  # type: ignore
                    "Не удалось кикнуть пользователя.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True)

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "Пользователь кикнут",  # type: ignore
                f"Пользователь <@{member.id}> был кикнут модератором {interaction.user.mention}",  # noqa: E501
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            )
        )
        logger.info(
            "[command] - invoked user=%s guild=%s target=%s reason=%s",
            interaction.user.id,
            guild.id,
            user.id,
            reason,
        )


async def setup(bot: "Nightcore"):
    """Setup the Kick cog."""
    await bot.add_cog(Kick(bot))
