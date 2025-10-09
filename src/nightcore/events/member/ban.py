"""Handle member ban events."""

import logging
from datetime import datetime, timezone

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_specified_channel
from src.nightcore.bot import Nightcore
from src.nightcore.utils import (
    ensure_messageable_channel_exists,
)

logger = logging.getLogger(__name__)


class BanMemberEvent(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Handle member ban event."""

        async with self.bot.uow.start() as session:
            if not (
                logging_members_channel_id := await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_BANS,
                )
            ):
                logger.warning(
                    f"[logging] Logging channel (bans) not configured for guild {guild.id}"  # noqa: E501
                )
                return

        if not (
            logging_channel := await ensure_messageable_channel_exists(
                guild, logging_members_channel_id
            )
        ):
            logger.warning(
                f"[logging] Logging channel (bans) not found in guild {guild.id}"  # noqa: E501
            )
            return

        embed = discord.Embed(
            title="Пользователь был заблокирован",
            description=f"{user.mention} ({user.id})",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )

        async for entry in guild.audit_logs(
            limit=5, action=discord.AuditLogAction.ban
        ):
            if entry.target.id == user.id:  # type: ignore
                embed.add_field(
                    name="Модератор",
                    value=f"{entry.user.mention}",  # type: ignore
                    inline=False,
                )
                embed.add_field(
                    name="Причина блокировки",
                    value=entry.reason or "Не указана",  # noqa: RUF001
                    inline=False,
                )
                break

        embed.set_footer(
            text="Powered by nightcore",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        try:
            await logging_channel.send(embed=embed)  # type: ignore
        except Exception as e:
            logger.error(f"Failed to send member join log message: {e}")
            return

        logger.info("[logging] Member ban logged for guild: %s", guild.id)


async def setup(bot: Nightcore):
    """Setup the BanMemberEvent cog."""
    await bot.add_cog(BanMemberEvent(bot))
