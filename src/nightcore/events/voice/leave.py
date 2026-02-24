import logging  # noqa: D100
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import discord
from discord import Embed, Member, VoiceChannel, VoiceState
from discord.ext.commands import Cog  # type: ignore

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


class VoiceStateLeaveEvent(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @Cog.listener()
    async def on_voice_channel_leave(
        self,
        member: Member,
        before: VoiceState,
        logging_channel_id: int | None,
    ) -> None:
        """Handle voice channel leave events."""

        guild = member.guild
        before_channel = cast(VoiceChannel, before.channel)

        if not logging_channel_id:
            logger.info(
                "[voice/leave] No logging channel configured for guild %s",
                guild.id,
            )
            return

        channel = await ensure_messageable_channel_exists(
            guild, logging_channel_id
        )
        if not channel:
            logger.info(
                "[voice/leave] Logging channel with ID %s not found in guild %s",  # noqa: E501
                logging_channel_id,
                guild.id,
            )
            return

        embed = Embed(
            title="Участник вышел из голосового канала",
            color=discord.Color.red(),
            timestamp=datetime.now(UTC),
        )

        embed.add_field(
            name="Участник",
            value=f"{member.mention} (`{member.id}`)",
            inline=False,
        )
        embed.add_field(
            name="Канал",
            value=f"{before_channel.mention} (`{before_channel.id}`)",
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
    """Setup the VoiceStateLeaveEvent cog."""
    await bot.add_cog(VoiceStateLeaveEvent(bot))
