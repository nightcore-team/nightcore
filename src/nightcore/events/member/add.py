"""Handle member add events."""

import logging
from datetime import UTC, datetime

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_specified_channel
from src.nightcore.bot import Nightcore
from src.nightcore.utils import (
    discord_ts,
    ensure_messageable_channel_exists,
)

logger = logging.getLogger(__name__)


class AddMemberEvent(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Handle member join event."""
        guild = member.guild

        async with self.bot.uow.start() as session:
            if not (
                logging_members_channel_id := await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_MEMBERS,
                )
            ):
                logger.warning(
                    f"[logging] Logging channel (members) not configured for guild {guild.id}"  # noqa: E501
                )
                return

        if not (
            logging_channel := await ensure_messageable_channel_exists(
                guild, logging_members_channel_id
            )
        ):
            logger.warning(
                f"[logging] Logging channel (members) not found in guild {guild.id}"  # noqa: E501
            )
            return

        embed = discord.Embed(
            title="Пользователь присоединился к серверу",
            description=f"{member.mention} ({member.id})",
            color=discord.Color.green(),
            timestamp=datetime.now(UTC),
        )
        embed.add_field(
            name="Дата регистрации",
            value=discord_ts(member.created_at),
            inline=False,
        )
        if member.bot:
            async for entry in guild.audit_logs(
                limit=5, action=discord.AuditLogAction.bot_add
            ):
                if entry.target.id == member.id:  # type: ignore
                    embed.add_field(
                        name="Добавлен бот",
                        value=f"{entry.user.mention}",  # type: ignore
                        inline=False,
                    )

        embed.set_footer(
            text="Powered by nightcore",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        try:
            await logging_channel.send(embed=embed)  # type: ignore
        except Exception as e:
            logger.error(f"Failed to send member join log message: {e}")
            return

        logger.info("[logging] Member join logged for guild: %s", guild.id)


async def setup(bot: Nightcore):
    """Setup the AddMemberEvent cog."""
    await bot.add_cog(AddMemberEvent(bot))
