"""Handle role creation events."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.operations import get_specified_webhook
from src.utils._enums import ChannelType

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.webhook import send_to_webhook

logger = logging.getLogger(__name__)


class UpdateRoleEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    def _enabled_permission_names(
        self, perms: discord.Permissions
    ) -> list[str]:
        return [name for name, value in dict(perms).items() if value]

    @Cog.listener()
    async def on_guild_role_update(
        self, before: discord.Role, after: discord.Role
    ):
        """Handle role deletion events."""

        guild = after.guild

        embed = discord.Embed(
            title="Изменение роли",
            description=f"Роль {after.mention} ({after.id}) была изменена",
            color=discord.Color.blurple(),
            timestamp=datetime.now(UTC),
        )
        embed.set_footer(
            text="Powered by nightcore",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        # name
        if before.name != after.name:
            embed.add_field(
                name="Название",
                value=f"`{before.name}` → `{after.name}`",
                inline=True,
            )

        # color
        if int(before.color.value) != int(after.color.value):
            old_color = f"#{before.color.value:06X}"
            new_color = f"#{after.color.value:06X}"
            embed.add_field(
                name="Цвет",
                value=f"{old_color} → {new_color}",
                inline=True,
            )

        # Отдельно в списке (hoist)
        if bool(before.hoist) != bool(after.hoist):
            old_hoist = "да" if before.hoist else "нет"
            new_hoist = "да" if after.hoist else "нет"
            embed.add_field(
                name="Отдельно в списке",
                value=f"{old_hoist} → {new_hoist}",
                inline=True,
            )

        # mentionable
        if bool(before.mentionable) != bool(after.mentionable):
            old_mention = "да" if before.mentionable else "нет"
            new_mention = "да" if after.mentionable else "нет"
            embed.add_field(
                name="Упоминаемая",
                value=f"{old_mention} → {new_mention}",
                inline=True,
            )

        # permissions
        if before.permissions != after.permissions:
            old_perms = set(self._enabled_permission_names(before.permissions))
            new_perms = set(self._enabled_permission_names(after.permissions))

            changes: list[str] = []

            # added permissions
            for perm in sorted(new_perms - old_perms):
                changes.append(f"* {perm}: ✔")
            # removed permissions
            for perm in sorted(old_perms - new_perms):
                changes.append(f"* {perm}: ✘")

            embed.add_field(
                name="Права",
                value="\n".join(changes) if changes else "—",
                inline=False,
            )

        # send only if there are changes
        if len(embed.fields) == 0:
            return

        async with self.bot.uow.start() as session:
            roles_logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ROLES,
            )

        if not roles_logging_webhook:
            logger.info(
                "[roles] Logging channel (roles) not configured for guild %s",
                guild.id,
            )
            return

        if not roles_logging_webhook.valid:
            logger.info(
                "[roles] Logging webhook (roles) invalid in guild %s",
                guild.id,
            )
            return

        await send_to_webhook(
            self.bot,
            roles_logging_webhook,
            embed,
            context="role/update",
            guild_id=guild.id,
        )

        logger.info(
            "[roles] Role update logged for guild %s, role %s",
            guild.id,
            after.id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the UpdateRoleEvent cog."""
    await bot.add_cog(UpdateRoleEvent(bot))
