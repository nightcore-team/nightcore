"""Unmute in marketplace command for the Nightcore bot."""

import logging
from datetime import UTC, datetime
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
from src.nightcore.features.moderation.utils.transformers import (
    StringToRuleTransformer,
)
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


class UnVMute(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(  # type: ignore
        name="unvmute",
        description="Снять пользователю блокировку голосовых каналов",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        user="Пользователь для размута",
        reason="Причина размута пользователя",
    )
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def unvmute(
        self,
        interaction: Interaction,
        user: Member,
        reason: app_commands.Transform[
            app_commands.Range[str, 1, 1000], StringToRuleTransformer
        ],
    ):
        """Unmute a user in the server."""
        guild = cast(Guild, interaction.guild)

        # Ensure we have a guild Member object
        member = user

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildModerationConfig,
        ) as (guild_config, _):
            mute_role_id = guild_config.vmute_role_id

        if not guild.me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "У меня нет прав для размута участников.",
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка снятия блокировки",
                    "Вы не можете размутить меня.",
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
                    "Я не могу размутить этого пользователя, потому что у него роль выше моей.",  # noqa: E501
                ),
                ephemeral=True,
            )

        mrole = None
        if mute_role_id:
            mrole = await ensure_role_exists(guild, mute_role_id)

        if not mute_role_id or mrole is None:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка снятия блокировки",
                    f"Роль мута с ID {mute_role_id} не найдена на этом сервере.",  # noqa: E501
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
                        "Роль мута не найдена у этого пользователя.",
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
                        "Failed to remove mute role %s from user %s: %s",
                        mute_role_id,
                        member.id,
                        e,
                    )
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка снятия блокировки",
                            "Не удалось удалить роль мута у пользователя.",
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
                punish_type="unvmute",
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
                    category="vmute",
                    mute_type="vmute",
                    guild_id=guild.id,
                    moderator_id=interaction.user.id,
                    user_id=member.id,
                    reason=reason,
                    created_at=datetime.now(UTC),
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
    """Setup the UnVMute cog."""
    await bot.add_cog(UnVMute(bot))
