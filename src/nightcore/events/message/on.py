"""Message events module."""

import logging

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import MainGuildConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_specified_channel
from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class OnMessageEvent(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle message create events."""

        guild = message.guild

        if not guild:
            if not message.attachments:
                return
            try:
                self.bot.dispatch("stats_provided", message)
            except Exception as e:
                logger.error("Failed to dispatch stats_provided event: %s", e)

        else:
            async with self.bot.uow.start() as session:
                if not (
                    proposal_channel_id := await get_specified_channel(
                        session,
                        guild_id=guild.id,
                        config_type=MainGuildConfig,
                        channel_type=ChannelType.CREATE_PROPOSALS,
                    )
                ):
                    logger.error(
                        "[proposals] No proposal channel found for guild %s",
                        guild.id,
                    )

            if message.channel.id == proposal_channel_id:
                self.bot.dispatch("create_proposal", message)
                return

        logger.info("[message] Message received: %s", message)

        return


async def setup(bot: Nightcore) -> None:
    """Setup the OnMessageEvent cog."""
    await bot.add_cog(OnMessageEvent(bot))
