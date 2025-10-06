import logging
from typing import cast

import discord
from discord import Guild
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_specified_channel
from src.nightcore.bot import Nightcore
from src.nightcore.utils import discord_ts, ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


class CreateChannelHandler(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Handle guild channel create event."""
        guild = cast(Guild, channel.guild)  # type: ignore

        async with self.bot.uow.start() as session:
            if not (
                logging_channels_channel_id := await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_CHANNELS,
                )
            ):
                logger.warning(
                    f"[logging] Logging channel (channels) not configured for guild {guild.id}"  # noqa: E501
                )
                return

        if not (
            logging_channel := await ensure_messageable_channel_exists(
                guild, logging_channels_channel_id
            )
        ):
            logger.warning(
                f"[logging] Logging channel (channels) not found in guild {guild.id}"  # noqa: E501
            )
            return

        try:
            async for entry in guild.audit_logs(
                limit=5, action=discord.AuditLogAction.channel_create
            ):
                if entry.target.id == channel.id:  # type: ignore
                    embed = discord.Embed(
                        title="Канал создан",
                        color=discord.Color.green(),
                        timestamp=channel.created_at,
                    )
                    embed.add_field(name="Канал", value=f"{channel.mention}")
                    embed.add_field(name="ID канала", value=channel.id)
                    embed.add_field(
                        name="Создан",
                        value=discord_ts(channel.created_at, "R"),
                    )
                    embed.add_field(
                        name="Тип канала",
                        value=str(channel.type)
                        .split(".")[-1]
                        .replace("_", " ")
                        .title(),
                    )
                    embed.set_footer(
                        text="Powered by nightcore",
                        icon_url=self.bot.user.display_avatar.url,  # type: ignore
                    )
                    if entry.user:
                        embed.add_field(
                            name="Создатель",
                            value=f"{entry.user.mention} ({entry.user.id})",
                            inline=False,
                        )
                    await logging_channel.send(embed=embed)  # type: ignore
                    return

        except Exception as e:
            logger.exception(
                "[logging] Failed to check audit log for channel create: %s", e
            )


async def setup(bot: Nightcore):
    """Setup the CreateChannelHandler cog."""
    await bot.add_cog(CreateChannelHandler(bot))
