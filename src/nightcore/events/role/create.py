"""Handle role creation events."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_specified_channel

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


class CreateRoleEvent(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    def _format_permissions(self, perms: discord.Permissions) -> str:
        # build a string listing all granted permissions

        lines: list[str] = []
        for name, value in dict(perms).items():
            if value:
                lines.append(f"* {name}: ✔")
        return "\n".join(lines) if lines else "—"

    @Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Handle role creation events."""

        guild = role.guild

        async with self.bot.uow.start() as session:
            roles_logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ROLES,
            )

        if not roles_logging_channel_id:
            logger.error(
                "[roles] Logging channel (roles) not configured for guild %s",
                guild.id,
            )
            return

        channel = await ensure_messageable_channel_exists(
            guild, roles_logging_channel_id
        )

        if not channel:
            logger.error(
                "[roles] Logging channel (roles) not found in guild %s",
                guild.id,
            )
            return

        permissions_text = self._format_permissions(role.permissions)

        icon_hash = None
        icon_url = None
        if role.icon:
            icon_hash = getattr(role.icon, "key", None) or getattr(
                role.icon, "hash", None
            )
            try:
                icon_url = role.icon.url
            except Exception:
                icon_url = None

        icon_field_value = f"{icon_hash or '—'}\n{icon_url or '—'}"
        unicode_emoji_value = role.unicode_emoji or "—"

        embed = discord.Embed(
            title="Роль создана",
            description=f"{role.mention} ({role.id})",
            color=discord.Color.blurple(),
            timestamp=datetime.now(UTC),
        )
        embed.set_footer(
            text="Powered by nightcore",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        embed.add_field(
            name="Отображается отдельно",
            value=str(bool(role.hoist)),
            inline=True,
        )
        embed.add_field(
            name="Роль интеграции", value=str(bool(role.managed)), inline=True
        )
        embed.add_field(name="Эмодзи", value=unicode_emoji_value, inline=True)
        embed.add_field(name="Позиция", value=str(role.position), inline=True)
        embed.add_field(
            name="Упоминаемая", value=str(bool(role.mentionable)), inline=True
        )
        embed.add_field(
            name="Цвет",
            value=str(role.color.value),
            inline=True,
        )
        embed.add_field(name="Иконка", value=icon_field_value, inline=True)
        embed.add_field(name="Права", value=permissions_text, inline=False)

        created_by_value = None
        if not role.managed:
            try:
                async for entry in guild.audit_logs(
                    limit=5, action=discord.AuditLogAction.role_create
                ):
                    # entry.target should be a discord.Role
                    if (
                        isinstance(entry.target, discord.Role)
                        and entry.target.id == role.id
                    ):
                        executor = entry.user
                        created_by_value = (
                            executor.mention if executor else "—"
                        )
                        break
            except discord.Forbidden:
                created_by_value = "—"
            except Exception:
                created_by_value = "—"
        else:
            created_by_value = "Бот при входе на сервер"

        if created_by_value:
            embed.add_field(
                name="Создал", value=created_by_value, inline=False
            )

        try:
            await channel.send(embed=embed)  # type: ignore
        except Exception as e:
            logger.exception(
                "[roles] Failed to send role creation log in guild %s: %s",
                guild.id,
                e,
            )
            return

        logger.info(
            "[roles] Role creation logged for guild %s, role %s",
            guild.id,
            role.id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the CreateRoleEvent cog."""
    await bot.add_cog(CreateRoleEvent(bot))
