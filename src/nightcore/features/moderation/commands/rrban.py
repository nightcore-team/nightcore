"""Role requesting ban command for the Nightcore bot."""

import logging
from datetime import timezone
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.operations import (
    get_moderation_access_roles,
    get_or_create_user,
    set_user_field_upsert,
)
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.events import UserMutedEventData
from src.nightcore.utils import (
    ensure_member_exists,
    has_any_role_from_sequence,
)
from src.nightcore.utils.time_utils import parse_duration

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Rrban(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(
        name="rrban",
        description="Заблокировать пользователю возможность запрашивать роли",
    )
    @app_commands.describe(
        user="Пользователь для блокировки", reason="Причина блокировки"
    )
    async def rrban(
        self,
        interaction: Interaction,
        user: discord.User,
        duration: str,
        reason: str,
    ):
        """Ban a user from requesting roles."""
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
                        "Вы не можете заблокировать запрос ролей для модераторов.",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            try:
                u, _ = await get_or_create_user(
                    session, guild_id=guild.id, user_id=member.id
                )
                if u.role_request_ban:
                    return await interaction.response.send_message(
                        embed=ValidationErrorEmbed(
                            "Этот пользователь уже заблокирован на запрос ролей.",  # noqa: E501
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

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
                    category=self.__class__.__name__.lower(),
                    moderator=interaction.user,  # type: ignore
                    user=member,
                    reason=reason,
                    created_at=discord.utils.utcnow().astimezone(
                        tz=timezone.utc
                    ),
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
            embed=SuccessMoveEmbed(
                "Блокировка на запрос ролей",
                f"Модератора {interaction.user.mention} заблокировал запрос ролей пользователю <@{member.id}>",  # noqa: E501
                self.bot.user.name,  # type: ignore
                self.bot.user.display_avatar.url,  # type: ignore
            )
            .add_field(name="Причина", value=reason, inline=True)
            .add_field(name="Длительность", value=duration, inline=True)
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
