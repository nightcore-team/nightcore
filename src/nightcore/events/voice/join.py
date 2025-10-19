import logging  # noqa: D100
from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

import discord
from discord import Embed, Member, VoiceChannel, VoiceState
from discord.ext.commands import Cog  # type: ignore

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


class VoiceStateJoinEvent(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @Cog.listener()
    async def on_voice_channel_join(
        self,
        member: Member,
        after: VoiceState,
        logging_channel_id: int | None,
    ) -> None:
        """Handle voice channel join events."""

        guild = member.guild
        after_channel = cast(VoiceChannel, after.channel)

        if not logging_channel_id:
            logger.error(
                "[voice/join] No logging channel configured for guild %s",
                guild.id,
            )
            return

        channel = await ensure_messageable_channel_exists(
            guild, logging_channel_id
        )
        if not channel:
            logger.error(
                "[voice/join] Logging channel with ID %s not found in guild %s",  # noqa: E501
                logging_channel_id,
                guild.id,
            )
            return

        embed = Embed(
            title="Участник зашёл в голосовой канал",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )

        embed.add_field(
            name="Участник",
            value=f"{member.mention} (`{member.id}`)",
            inline=False,
        )
        embed.add_field(
            name="Канал",
            value=f"{after_channel.mention} (`{after_channel.id}`)",
            inline=False,
        )

        embed.set_footer(
            text="Powered by nightcore",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        try:
            await channel.send(embed=embed)  # type: ignore
        except Exception as e:
            logger.error(
                "[voice/join] Failed to send log message to channel %s in guild %s: %s",  # noqa: E501
                logging_channel_id,
                guild.id,
                e,
            )


async def setup(bot: "Nightcore") -> None:
    """Setup the VoiceStateJoinEvent cog."""
    await bot.add_cog(VoiceStateJoinEvent(bot))
