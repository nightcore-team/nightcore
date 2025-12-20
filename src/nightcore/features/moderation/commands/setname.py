"""Setname command for the Nightcore bot."""

import logging
from datetime import UTC
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import get_moderation_access_roles
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.moderation.events import (
    UserSetNameEventData,
)
from src.nightcore.features.moderation.utils.transformers import (
    StringToRuleTransformer,
)
from src.nightcore.utils import (
    compare_top_roles,
    has_any_role_from_sequence,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Setname(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="setname",
        description="Установить никнейм пользователю",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        user="Пользователь для изменения никнейма",
        reason="Причина изменения никнейма",
        nickname="Новый никнейм пользователя (оставьте пустым, чтобы восстановить оригинальный)",  # noqa: E501
    )
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def setname(
        self,
        interaction: Interaction,
        user: Member,
        reason: app_commands.Transform[
            app_commands.Range[str, 1, 1000], StringToRuleTransformer
        ],
        nickname: str | None = None,
    ):
        """Set/restore a user's nickname."""
        guild = cast(Guild, interaction.guild)

        # Ensure we have a guild Member object
        member = user

        # check moderation access
        async with self.bot.uow.start() as session:
            moderation_access_roles = await get_moderation_access_roles(
                session, guild_id=guild.id
            )

        is_member_moderator = has_any_role_from_sequence(
            member, moderation_access_roles
        )
        if is_member_moderator:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка смены никнейма",
                    "Вы не можете изменить никнейм модератора.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not guild.me.guild_permissions.change_nickname:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "У меня нет прав на изменение никнеймов.",
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка смены никнейма",
                    "Вы не можете изменить мой никнейм.",
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
                    "Я не могу изменить никнейм этого пользователя, потому что у него роль выше моей.",  # noqa: E501
                ),
                ephemeral=True,
            )

        old_member_nickname = member.display_name

        if nickname:
            if len(nickname) > 32:
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        "Никнейм не может быть длиннее 32 символов.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
        else:
            nickname = member.global_name or member.name

        await interaction.response.defer(thinking=True)

        try:
            self.bot.dispatch(
                "user_setname",
                data=UserSetNameEventData(
                    moderator=interaction.user,  # type: ignore
                    user=member,
                    category=self.__class__.__name__.lower(),
                    reason=reason,
                    old_nickname=old_member_nickname,
                    new_nickname=nickname,
                    created_at=discord.utils.utcnow().astimezone(UTC),
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_setname event: %s", e
            )
            return

        try:
            await member.edit(nick=nickname)
        except Exception as e:
            logger.exception("[command] - Failed to set user nickname: %s", e)
            return

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "Никнейм изменён",
                f"Никнейм пользователя {member.mention} успешно изменён.",
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            )
        )
        logger.info(
            "[command] - invoked user=%s guild=%s target=%s reason=%s old_nickname=%s new_nickname=%s",  # noqa: E501
            interaction.user.id,
            guild.id,
            user.id,
            reason,
            old_member_nickname if old_member_nickname else "No Nickname",
            nickname if nickname else "No Nickname",
        )


async def setup(bot: "Nightcore"):
    """Setup the Setname cog."""
    await bot.add_cog(Setname(bot))
