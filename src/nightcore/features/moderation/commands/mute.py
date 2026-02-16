"""Command to mute a user."""

import logging
from datetime import UTC
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildModerationConfig
from src.nightcore.features.moderation.utils.transformers import (
    StringToRuleTransformer,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.moderation.components.v2 import PunishViewV2
from src.nightcore.features.moderation.events import UserMutedEventData
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import (
    compare_top_roles,
    ensure_role_exists,
    has_any_role,
    has_any_role_from_sequence,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.time_utils import calculate_end_time, parse_duration

logger = logging.getLogger(__name__)


class Mute(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="mute", description="Заблокировать чат пользователю"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        user="Пользователь для блокировки",
        duration="Длительность блокировки",
        reason="Причина блокировки",
    )
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def mute(
        self,
        interaction: Interaction,
        user: Member,
        duration: str,
        reason: app_commands.Transform[
            app_commands.Range[str, 1, 1000], StringToRuleTransformer
        ],
    ):
        """Mute a user in the server."""
        guild = cast(Guild, interaction.guild)

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

        member = user

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildModerationConfig,
            _create=False,
        ) as (guild_config, _):
            moderation_access_roles = guild_config.moderation_access_roles_ids

        mute_type = guild_config.mute_type

        is_member_moderator = has_any_role_from_sequence(
            member, moderation_access_roles
        )
        if is_member_moderator:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка блокировки",
                    "Вы не можете заблокировать чат модераторам.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if member.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка блокировки",
                    "Вы не можете заблокировать чат администраторам.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if mute_type == "role":
            if not guild.me.guild_permissions.manage_roles:
                return await interaction.response.send_message(
                    embed=MissingPermissionsEmbed(
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                        "У меня нет прав для блокировки чата участников.",
                    ),
                    ephemeral=True,
                )
        elif mute_type == "timeout":  # noqa: SIM102
            if not guild.me.guild_permissions.moderate_members:
                return await interaction.response.send_message(
                    embed=MissingPermissionsEmbed(
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                        "У меня нет прав для блокировки чата участников.",
                    ),
                    ephemeral=True,
                )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка блокировки",
                    "Вы не можете заблокировать чат мне.",
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
                    "Я не могу заблокировать чат этому пользователю, потому что у него роль выше моей.",  # noqa: E501
                ),
                ephemeral=True,
            )

        end_time = calculate_end_time(parsed_duration)

        match mute_type:
            case "role":
                mute_role_id = guild_config.mute_role_id
                if mute_role_id:
                    # Try cache first
                    mrole = await ensure_role_exists(guild, mute_role_id)
                    if mrole is None:
                        return await interaction.response.send_message(
                            embed=ErrorEmbed(
                                "Роль блокировки не найдена",
                                f"Роль блокировки с ID {mute_role_id} не найдена на этом сервере.",  # noqa: E501
                                self.bot.user.name,  # type: ignore
                                self.bot.user.display_avatar.url,  # type: ignore
                            ),
                            ephemeral=True,
                        )
                else:
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Роль блокировки не найдена",
                            f"Роль блокировки с ID {mute_role_id} не настроена.",  # noqa: E501
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

                has_role = has_any_role(member, mrole.id)

                if not has_role:
                    try:
                        await member.add_roles(mrole, reason=reason)  # type: ignore
                    except Exception as e:
                        logger.exception("Failed to add role: %s", e)
                        return await interaction.response.send_message(
                            embed=ErrorEmbed(
                                "Ошибка добавления роли",
                                "Не удалось добавить роль блокировки пользователю.",  # noqa: E501
                                self.bot.user.name,  # type: ignore
                                self.bot.user.display_avatar.url,  # type: ignore
                            ),
                            ephemeral=True,
                        )
                else:
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка блокировки",
                            f"У {member.mention} уже есть блокировка чата.",
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

            case "timeout":
                try:
                    if not member.is_timed_out():
                        await member.timeout(end_time, reason=reason)
                    else:
                        return await interaction.response.send_message(
                            embed=ErrorEmbed(
                                "Ошибка блокировки",
                                f"{member.mention} уже в тайм-ауте.",
                                self.bot.user.name,  # type: ignore
                                self.bot.user.display_avatar.url,  # type: ignore
                            ),
                            ephemeral=True,
                        )

                except Exception as e:
                    logger.exception("Failed to timeout member: %s", e)
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка тайм-аута",
                            "Не удалось установить тайм-аут пользователю.",
                            self.bot.user.name,  # type: ignore
                            self.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
            case _:
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Неизвестный тип блокировки",
                        "Тип блокировки должен быть 'role' или 'timeout'.",
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

        await interaction.response.defer(thinking=True)

        await interaction.followup.send(
            view=PunishViewV2(
                self.bot,
                user=member,
                punish_type="mute",
                moderator_id=interaction.user.id,
                duration=duration,
                reason=reason,
                mode="server",
            ),
            ephemeral=False,
        )

        try:
            self.bot.dispatch(
                "user_muted",
                data=UserMutedEventData(
                    mode="dm",
                    category=self.__class__.__name__.lower(),
                    moderator=interaction.user,  # type: ignore
                    user=member,
                    reason=reason,
                    created_at=discord.utils.utcnow().astimezone(tz=UTC),
                    guild_name=guild.name,
                    duration=parsed_duration,
                    original_duration=duration,
                    end_time=end_time,  # type: ignore
                ),
            )
        except Exception as e:
            logger.exception(
                "[event] - Failed to dispatch user_muted event: %s", e
            )
            return

        logger.info(
            "[command] - invoked user=%s guild=%s target=%s reason=%s",
            interaction.user.id,
            guild.id,
            member.id,
            reason,
        )


async def setup(bot: "Nightcore"):
    """Setup the Mute cog."""
    await bot.add_cog(Mute(bot))
