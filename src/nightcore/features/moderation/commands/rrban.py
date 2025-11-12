"""Role requesting ban command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import (
    get_moderation_access_roles,
    get_or_create_user,
    set_user_field_upsert,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.moderation.components.v2 import PunishViewV2
from src.nightcore.features.moderation.events import UserMutedEventData
from src.nightcore.utils import (
    has_any_role_from_sequence,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.time_utils import parse_duration

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Rrban(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="rrban",
        description="Заблокировать пользователю возможность запрашивать роли",
    )
    @app_commands.describe(
        user="Пользователь для блокировки", reason="Причина блокировки"
    )
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def rrban(
        self,
        interaction: Interaction,
        user: Member,
        duration: str,
        reason: str,
    ):
        """Ban a user from requesting roles."""
        guild = cast(Guild, interaction.guild)

        # Ensure we have a guild Member object
        member = user

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете заблокировать запрос ролей для меня.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        parsed_duration = parse_duration(duration)

        if not parsed_duration:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Неверная продолжительность. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        async with self.bot.uow.start() as session:
            moderation_access_roles = await get_moderation_access_roles(
                session, guild_id=guild.id
            )
            u, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=member.id
            )

        is_member_moderator = has_any_role_from_sequence(
            member, moderation_access_roles
        )
        if is_member_moderator:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете заблокировать запрос ролей для модераторов.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            if u.role_request_ban:
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        "Этот пользователь уже заблокирован на запрос ролей.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            async with self.bot.uow.start() as session:
                await set_user_field_upsert(
                    session,
                    guild_id=guild.id,
                    user_id=member.id,
                    field="role_request_ban",
                    value=True,
                )

        except Exception as e:
            logger.error(
                "Failed to role request ban user %s in guild %s: %s",
                user.id,
                guild.id,
                e,
            )
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка блокировки на запрос ролей",
                    "Не удалось заблокировать пользователю возможность запрашивать роли.",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )

        await interaction.response.defer(thinking=True)

        try:
            self.bot.dispatch(
                "user_role_request_banned",
                data=UserMutedEventData(
                    mode="dm",
                    category=self.__class__.__name__.lower(),
                    moderator=interaction.user,  # type: ignore
                    user=member,
                    reason=reason,
                    created_at=discord.utils.utcnow().astimezone(
                        tz=timezone.utc
                    ),
                    guild_name=guild.name,
                    duration=parsed_duration,
                    original_duration=duration,
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_role_request_banned event: %s",  # noqa: E501
                e,
            )
            return

        await interaction.followup.send(
            view=PunishViewV2(
                bot=self.bot,
                user=member,
                punish_type="rrban",
                moderator_id=interaction.user.id,  # type: ignore
                reason=reason,
                duration=duration,
                mode="server",
            )
        )

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s reason=%s duration=%s",  # noqa: E501
            interaction.user.id,
            guild.id,
            user.id,
            reason,
            duration,
        )


async def setup(bot: "Nightcore"):
    """Setup the Rrban cog."""
    await bot.add_cog(Rrban(bot))
