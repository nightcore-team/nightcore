"""Command to mute a user in voice chat."""

import logging
from datetime import UTC
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.infra.db.models import GuildModerationConfig
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    MissingPermissionsViewV2,
    ValidationErrorViewV2,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.components.v2 import PunishViewV2
from src.nightcore.features.moderation.events import UserMutedEventData
from src.nightcore.features.moderation.utils.transformers import (
    StringToRuleTransformer,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import (
    compare_top_roles,
    ensure_role_exists,
    has_any_role,
    has_any_role_from_sequence,
)
from src.nightcore.utils.time_utils import calculate_end_time, parse_duration

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class VMute(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="vmute",
        description="Выдать пользователю блокировку голосовых каналов.",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        user="Пользователь для блокировки",
        reason="Причина блокировки пользователя",
    )
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def vmute(
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

        # Ensure we have a guild Member object
        member = user

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildModerationConfig,
        ) as (guild_config, _):
            moderation_access_roles = guild_config.moderation_access_roles_ids

        mute_role_id = guild_config.vmute_role_id

        is_member_moderator = has_any_role_from_sequence(
            member, moderation_access_roles
        )
        if is_member_moderator:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка блокировки",
                    "Вы не можете заблокировать модераторов.",
                ),
                ephemeral=True,
            )
            return

        if member.guild_permissions.administrator:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка блокировки",
                    "Вы не можете заблокировать администраторов.",
                ),
                ephemeral=True,
            )
            return

        if not guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                view=MissingPermissionsViewV2(
                    "У меня нет прав для блокировки участников.",
                ),
                ephemeral=True,
            )
            return

        if guild.me == member:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка блокировки",
                    "Вы не можете заблокировать меня.",
                ),
                ephemeral=True,
            )
            return

        if not compare_top_roles(guild, member):
            await interaction.response.send_message(
                view=MissingPermissionsViewV2(
                    "Я не могу заблокировать этого пользователя, "
                    "потому что у него роль выше моей.",
                ),
                ephemeral=True,
            )
            return

        parsed_duration = parse_duration(duration)

        if not parsed_duration:
            await interaction.response.send_message(
                view=ValidationErrorViewV2(
                    "Неверная продолжительность. "
                    "Используйте s/m/h/d (например, 1h, 1d, 7d).",
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        end_time = calculate_end_time(parsed_duration)

        if mute_role_id is None:
            raise FieldNotConfiguredError("vmute role")

        # Try cache first
        mrole = await ensure_role_exists(guild, mute_role_id)
        if mrole is None:
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка блокировки",
                    f"Не удалось найти роль блокировки с ID "
                    f"{mute_role_id} на этом сервере.",
                ),
                ephemeral=True,
            )
            return

        # Discord state is not DB - make idempotent
        if has_any_role(member, mrole.id):
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка блокировки",
                    f"{member.mention} уже заблокирован.",
                ),
                ephemeral=True,
            )
            return
        try:
            await member.add_roles(mrole, reason=reason)  # type: ignore
        except discord.Forbidden as e:
            logger.warning("Failed to add vmute role (forbidden): %s", e)
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка блокировки",
                    "Не удалось добавить роль мута пользователю.",
                ),
                ephemeral=True,
            )
            return
        except discord.HTTPException as e:
            logger.exception("Failed to add vmute role (http): %s", e)
            if has_any_role(member, mrole.id):
                await interaction.followup.send(
                    view=ErrorViewV2(
                        "Ошибка блокировки",
                        f"{member.mention} уже заблокирован.",
                    ),
                    ephemeral=True,
                )
                return
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка блокировки",
                    "Не удалось добавить роль мута пользователю.",
                ),
                ephemeral=True,
            )
            return
        except Exception as e:
            logger.exception("Failed to add role: %s", e)
            if has_any_role(member, mrole.id):
                await interaction.followup.send(
                    view=ErrorViewV2(
                        "Ошибка блокировки",
                        f"{member.mention} уже заблокирован.",
                    ),
                    ephemeral=True,
                )
                return
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка блокировки",
                    "Не удалось добавить роль мута пользователю.",
                ),
                ephemeral=True,
            )
            return

        if member.voice and member.voice.channel:
            try:
                await member.edit(voice_channel=None, reason=reason)
            except discord.Forbidden:
                logger.error(
                    "Missing permissions to kick user %s from voice in guild %s",  # noqa: E501
                    member.id,
                    guild.id,
                )
            except discord.HTTPException as e:
                logger.exception(
                    "Failed to kick user %s from voice in guild %s: %s",
                    member.id,
                    guild.id,
                    e,
                )

        # Dispatch after successful Discord action; handler is idempotent
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

        await interaction.followup.send(
            view=PunishViewV2(
                bot=self.bot,
                user_id=member.id,
                punish_type="vmute",
                moderator_id=interaction.user.id,
                reason=reason,
                duration=duration,
                mode="server",
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
    """Setup the VMute cog."""
    await bot.add_cog(VMute(bot))
