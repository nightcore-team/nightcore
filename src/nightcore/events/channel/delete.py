"""Handle guild channel delete events."""

import logging
from datetime import datetime, timezone
from typing import cast

import discord
from discord import Guild
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_specified_channel
from src.nightcore.bot import Nightcore
from src.nightcore.utils import (
    channel_type,
    discord_ts,
    ensure_messageable_channel_exists,
)

from .utils.overwrites import build_channel_overwrites_file  # type: ignore

logger = logging.getLogger(__name__)


class DeleteChannelHandler(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Handle guild channel delete event."""
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
                limit=5, action=discord.AuditLogAction.channel_delete
            ):
                if entry.target.id == channel.id:  # type: ignore
                    embed = discord.Embed(
                        title="Канал удалён",
                        color=discord.Color.red(),
                        timestamp=datetime.now(tz=timezone.utc),
                    )
                    embed.add_field(name="Канал", value=f"{channel.mention}")
                    embed.add_field(name="ID канала", value=channel.id)
                    embed.add_field(
                        name="Создан",
                        value=discord_ts(channel.created_at, "R"),
                    )
                    embed.add_field(
                        name="Тип канала",
                        value=channel_type(channel.type),  # type: ignore
                    )
                    embed.add_field(
                        name="NSFW",
                        value="Да"
                        if getattr(channel, "nsfw", False)
                        else "Нет",
                    )
                    if k := getattr(channel, "rate_limit_per_user", "N/A"):
                        embed.add_field(
                            name="Медленный режим",
                            value=k,
                        )

                    self._check_voice_channel(channel, embed)

                    embed.set_footer(
                        text="Powered by nightcore",
                        icon_url=self.bot.user.display_avatar.url,  # type: ignore
                    )
                    if entry.user:
                        embed.add_field(
                            name="Удалён пользователем",
                            value=f"{entry.user.mention} ({entry.user.id})",
                            inline=False,
                        )

                    file = None
                    try:
                        file = build_channel_overwrites_file(channel)
                    except Exception as e:
                        logger.exception(
                            "[logging] Failed to build channel overwrites file: %s",  # noqa: E501
                            e,
                        )

                    if file:
                        await logging_channel.send(  # type: ignore
                            embed=embed,
                            file=file,
                        )
                    else:
                        await logging_channel.send(  # type: ignore
                            embed=embed,
                        )
                    return

        except Exception as e:
            logger.exception(
                "[logging] Failed to check audit log for channel create: %s", e
            )

    def _check_voice_channel(
        self, channel: discord.abc.GuildChannel, embed: discord.Embed
    ) -> None:
        if channel.type == discord.ChannelType.voice:
            embed.add_field(
                name="Битрейт",
                value=getattr(channel, "bitrate", "N/A"),
            )
            embed.add_field(
                name="Макс. кол-во участников",
                value=getattr(channel, "user_limit", "N/A"),
            )


async def setup(bot: Nightcore):
    """Setup the DeleteChannelHandler cog."""
    await bot.add_cog(DeleteChannelHandler(bot))
