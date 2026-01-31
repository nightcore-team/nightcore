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


class VoiceStateSwitchEvent(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @Cog.listener()
    async def on_voice_channel_switch(
        self,
        member: Member,
        before: VoiceState,
        after: VoiceState,
        logging_channel_id: int | None,
    ) -> None:
        """Handle voice channel switch events."""

        guild = member.guild
        before_channel = cast(VoiceChannel, before.channel)
        after_channel = cast(VoiceChannel, after.channel)

        if not logging_channel_id:
            logger.error(
                "[voice/switch] No logging channel configured for guild %s",
                guild.id,
            )
            return

        channel = await ensure_messageable_channel_exists(
            guild, logging_channel_id
        )
        if not channel:
            logger.error(
                "[voice/switch] Logging channel with ID %s not found in guild %s",  # noqa: E501
                logging_channel_id,
                guild.id,
            )
            return

        embed = Embed(
            description=f"Участник {member.mention} перешел в другой голосовой канал",
            color=discord.Color.yellow(),
            timestamp=datetime.now(UTC),
        )

        embed.set_footer(
            text="Powered by nightcore",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        embed.add_field(name="Канал", value=after_channel.mention, inline=True)
        embed.add_field(
            name="Предыдущий канал", value=before_channel.mention, inline=True
        )

        try:
            await channel.send(embed=embed)  # type: ignore
        except Exception as e:
            logger.error(
                "[voice/switch] Failed to send log message to channel %s in guild %s: %s",  # noqa: E501
                logging_channel_id,
                guild.id,
                e,
            )


async def setup(bot: "Nightcore") -> None:
    """Setup the VoiceStateSwitchEvent cog."""
    await bot.add_cog(VoiceStateSwitchEvent(bot))
