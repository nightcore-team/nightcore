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


class VoiceStateSwitchEvent(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @Cog.listener()
    async def on_voice_channel_switch(
        self,
        member: Member,
        before: VoiceState,
        after: VoiceState,
        logging_webhook: "DiscordWebhook | None",
    ) -> None:
        """Handle voice channel switch events."""

        guild = member.guild
        before_channel = cast(VoiceChannel, before.channel)
        after_channel = cast(VoiceChannel, after.channel)

        if not logging_webhook:
            logger.info(
                "[voice/switch] No logging channel configured for guild %s",
                guild.id,
            )
            return

        if not logging_webhook.valid:
            logger.info(
                "[voice/switch] Logging webhook invalid in guild %s",
                guild.id,
            )
            return

        embed = Embed(
            description=f"Участник {member.mention} перешел в другой голосовой канал",  # noqa: E501
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

        await send_to_webhook(
            self.bot,
            logging_webhook,
            embed,
            context="voice/switch",
            guild_id=guild.id,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the VoiceStateSwitchEvent cog."""
    await bot.add_cog(VoiceStateSwitchEvent(bot))
