"""Handle guild channel update events."""

import logging
from datetime import datetime, timezone
from typing import cast

import discord
from discord import Guild
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models._enums import ChannelType
from src.infra.db.models.guild import GuildLoggingConfig
from src.infra.db.operations import get_specified_channel  # type: ignore
from src.nightcore.bot import Nightcore
from src.nightcore.utils import ensure_messageable_channel_exists

from .utils.overwrites import build_permission_changes_field  # type: ignore

logger = logging.getLogger(__name__)


class UpdateChannelHandler(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_guild_channel_update(
        self, old: discord.abc.GuildChannel, new: discord.abc.GuildChannel
    ):
        """Handle guild channel update event."""
        guild = cast(Guild, new.guild)  # type: ignore
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
        embed = discord.Embed(
            title="Изменение канала",
            description=f"Канал {new.mention} был изменен"
            if hasattr(new, "mention")
            else f"Канал {new.id} был изменен",
            color=discord.Color.yellow(),
            timestamp=datetime.now(tz=timezone.utc),
        )
        embed.set_footer(
            text="Powered by nightcore",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        # Поля змін
        self._check_name_change(old, new, embed)
        self._check_topic_change(old, new, embed)
        self._check_nsfw_change(old, new, embed)
        self._check_parent_change(old, new, embed)
        self._check_slowmode_change(old, new, embed)

        if new.type == discord.ChannelType.voice:
            self._check_bitrate_change(old, new, embed)
            self._check_user_limit_change(old, new, embed)

        perm_changes_text = build_permission_changes_field(old, new, guild)
        if perm_changes_text:
            embed.add_field(
                name="Изменения прав",
                value=perm_changes_text[:1024]
                if len(perm_changes_text) > 1024
                else perm_changes_text,
                inline=False,
            )

        if embed.fields:
            try:
                await logging_channel.send(embed=embed)  # type: ignore
            except Exception as e:
                logger.exception(
                    "[logging] Failed to send logging embed about channel updating: %s",  # noqa: E501
                    e,
                )
        else:
            logger.info(
                "[logging] No relevant changes detected for channel %s in guild %s, skipping logging",  # noqa: E501
                new.id,
                guild.id,
            )

    def _check_name_change(
        self,
        old: discord.abc.GuildChannel,
        new: discord.abc.GuildChannel,
        embed: discord.Embed,
    ):
        if getattr(old, "name", None) != getattr(new, "name", None):
            embed.add_field(
                name="Название",
                value=f"{getattr(old, 'name', '—')} → {getattr(new, 'name', '—')}",  # noqa: E501
                inline=True,
            )

    def _check_topic_change(
        self,
        old: discord.abc.GuildChannel,
        new: discord.abc.GuildChannel,
        embed: discord.Embed,
    ):
        old_topic = old.topic or "пусто"  # type: ignore
        new_topic = new.topic or "пусто"  # type: ignore
        embed.add_field(
            name="Описание",
            value=f"{old_topic} → {new_topic}",
            inline=True,
        )

    def _check_nsfw_change(
        self,
        old: discord.abc.GuildChannel,
        new: discord.abc.GuildChannel,
        embed: discord.Embed,
    ):
        old_nsfw = getattr(
            old, "is_nsfw", lambda: getattr(old, "nsfw", False)
        )()
        new_nsfw = getattr(
            new, "is_nsfw", lambda: getattr(new, "nsfw", False)
        )()
        if old_nsfw != new_nsfw:
            embed.add_field(
                name="NSFW", value=f"{old_nsfw} → {new_nsfw}", inline=True
            )

    def _check_parent_change(
        self,
        old: discord.abc.GuildChannel,
        new: discord.abc.GuildChannel,
        embed: discord.Embed,
    ):
        old_parent_id = getattr(getattr(old, "category", None), "id", None)
        new_parent_id = getattr(getattr(new, "category", None), "id", None)
        if old_parent_id != new_parent_id:

            def fmt(pid):  # type: ignore
                return f"<#{pid}> ({pid})" if pid else "нет"

            embed.add_field(
                name="Категория",
                value=f"{fmt(old_parent_id)} → {fmt(new_parent_id)}",
                inline=True,
            )

    def _check_slowmode_change(
        self,
        old: discord.abc.GuildChannel,
        new: discord.abc.GuildChannel,
        embed: discord.Embed,
    ):
        if (
            isinstance(old, discord.TextChannel)
            and isinstance(new, discord.TextChannel)
            and old.slowmode_delay != new.slowmode_delay
        ):

            def fmt(v: int):
                return f"{v} сек" if v > 0 else "выключен"

            embed.add_field(
                name="Медленный режим",
                value=f"{fmt(old.slowmode_delay)} → {fmt(new.slowmode_delay)}",
                inline=True,
            )

    def _check_bitrate_change(
        self,
        old: discord.abc.GuildChannel,
        new: discord.abc.GuildChannel,
        embed: discord.Embed,
    ):
        if (
            isinstance(old, discord.VoiceChannel)
            and isinstance(new, discord.VoiceChannel)
            and old.bitrate != new.bitrate
        ):
            embed.add_field(
                name="Битрейт",
                value=f"{old.bitrate // 1000}kbps → {new.bitrate // 1000}kbps",
                inline=True,
            )

    def _check_user_limit_change(
        self,
        old: discord.abc.GuildChannel,
        new: discord.abc.GuildChannel,
        embed: discord.Embed,
    ):
        if (
            isinstance(old, discord.VoiceChannel)
            and isinstance(new, discord.VoiceChannel)
            and old.user_limit != new.user_limit
        ):

            def fmt(v: int):
                return str(v) if v and v > 0 else "нет"

            embed.add_field(
                name="Лимит пользователей",
                value=f"{fmt(old.user_limit)} → {fmt(new.user_limit)}",
                inline=True,
            )


async def setup(bot: Nightcore) -> None:
    """Setup the UpdateChannelHandler cog."""
    await bot.add_cog(UpdateChannelHandler(bot))
