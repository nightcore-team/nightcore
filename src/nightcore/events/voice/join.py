import logging  # noqa: D100
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import discord
from discord import Embed, Member, VoiceChannel, VoiceState
from discord.ext.commands import Cog  # type: ignore

if TYPE_CHECKING:
    from src.infra.db.models.discord_webhook import DiscordWebhook
    from src.nightcore.bot import Nightcore

from src.nightcore.utils.webhook import send_to_webhook

logger = logging.getLogger(__name__)


class VoiceStateJoinEvent(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @Cog.listener()
    async def on_voice_channel_join(
        self,
        member: Member,
        after: VoiceState,
        logging_webhook: "DiscordWebhook | None",
    ) -> None:
        """Handle voice channel join events."""

        guild = member.guild
        after_channel = cast(VoiceChannel, after.channel)

        if not logging_webhook:
            logger.info(
                "[voice/join] No logging channel configured for guild %s",
                guild.id,
            )
            return

        if not logging_webhook.valid:
            logger.info(
                "[voice/join] Logging webhook invalid in guild %s",
                guild.id,
            )
            return

        embed = Embed(
            title="Участник зашёл в голосовой канал",
            color=discord.Color.blurple(),
            timestamp=datetime.now(UTC),
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

        await send_to_webhook(
            self.bot,
            logging_webhook,
            embed,
            context="voice/join",
            guild_id=guild.id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the VoiceStateJoinEvent cog."""
    await bot.add_cog(VoiceStateJoinEvent(bot))
