"""Unmute command for the Nightcore bot."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildModerationConfig
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
)
from src.nightcore.features.moderation.components.v2 import PunishViewV2
from src.nightcore.features.moderation.events import UserUnmutedEventData
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import (
    compare_top_roles,
    ensure_role_exists,
    has_any_role,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class UnMute(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="unmute", description="Разблокировать чат пользователю"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        user="Пользователь для разблокировки", reason="Причина разблокировки"
    )
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def unmute(
        self,
        interaction: Interaction,
        user: Member,
        reason: str,
    ):
        """Unmute a user in the server."""
        guild = cast(Guild, interaction.guild)

        member = user

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildModerationConfig,
            _create=False,
        ) as (guild_config, _):
            mute_type = guild_config.mute_type
            mute_role_id = guild_config.mute_role_id

        if (
            not guild.me.guild_permissions.moderate_members
            or not guild.me.guild_permissions.manage_roles
        ):
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "У меня нет прав для разблокировки чата участников.",
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка снятия блокировки",
                    "Вы не можете разблокировать чат мне.",
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
                    "Я не могу разблокировать чат этому пользователю, потому что у него роль выше моей.",  # noqa: E501
                ),
                ephemeral=True,
            )

        match mute_type:
            case "role":
                mrole = None
                if mute_role_id:
                    mrole = await ensure_role_exists(guild, mute_role_id)

                if mute_role_id is None or mrole is None:
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка снятия блокировки",
                            f"Роль блокировки с ID {mute_role_id} не найдена на этом сервере.",  # noqa: E501
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                else:
                    has_role = has_any_role(member, mrole.id)

                    if not has_role:
                        return await interaction.response.send_message(
                            embed=ErrorEmbed(
                                "Ошибка снятия блокировки",
                                "Роль блокировки не найдена у этого пользователя.",  # noqa: E501
                                self.bot.user.name,  # type: ignore
                                self.bot.user.display_avatar.url,  # type: ignore
                            ),
                            ephemeral=True,
                        )
                    else:
                        try:
                            await member.remove_roles(mrole)
                        except Exception as e:
                            logger.exception(
                                "Failed to remove mute role %s from user %s: %s",  # noqa: E501
                                mute_role_id,
                                member.id,
                                e,
                            )
                            return await interaction.response.send_message(
                                embed=ErrorEmbed(
                                    "Ошибка снятия блокировки",
                                    "Не удалось снять роль мута с пользователя.",  # noqa: E501
                                    self.bot.user.name,  # type: ignore
                                    self.bot.user.display_avatar.url,  # type: ignore
                                ),
                                ephemeral=True,
                            )

            case "timeout":
                if member.is_timed_out():
                    try:
                        await member.timeout(None, reason=reason)
                    except Exception as e:
                        logger.exception(
                            "Failed to remove timeout from user %s: %s",
                            member.id,
                            e,
                        )
                        return await interaction.response.send_message(
                            embed=ErrorEmbed(
                                "Ошибка снятия блокировки",
                                "Не удалось снять тайм-аут.",
                                self.bot.user.name,  # type: ignore
                                self.bot.user.display_avatar.url,  # type: ignore
                            ),
                            ephemeral=True,
                        )
                else:
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка снятия блокировки",
                            "У пользователя в данный момент нет тайм-аута.",
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
            case _:
                logger.error(
                    "Unknown mute type for user %s",
                    member.id,
                )
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка снятия блокировки",
                        "Указанный тип блокировки неизвестен.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
        await interaction.response.defer(thinking=True)

        await interaction.followup.send(
            view=PunishViewV2(
                bot=self.bot,
                user=member,
                punish_type="unmute",
                moderator_id=interaction.user.id,  # type: ignore
                reason=reason,
                mode="server",
            )
        )

        try:
            self.bot.dispatch(
                "user_unmute",
                data=UserUnmutedEventData(
                    mode="dm",
                    category="mute",
                    mute_type="default",
                    guild_id=guild.id,
                    moderator_id=interaction.user.id,
                    user_id=member.id,
                    reason=reason,
                    created_at=datetime.now(timezone.utc),
                ),
                by_command=True,
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_unmuted event: %s", e
            )
            return

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s reason=%s",
            interaction.user.id,
            guild.id,
            user.id,
            reason,
        )


async def setup(bot: "Nightcore"):
    """Setup the UnMute cog."""
    await bot.add_cog(UnMute(bot))
