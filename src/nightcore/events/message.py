"""Message events module."""

# from typing import cast
import logging

import discord
from discord.ext.commands import Cog
from discord.raw_models import RawMessageDeleteEvent, RawMessageUpdateEvent

# from src.infra.db.models.enums import LoggingChannelType
# from src.infra.db.operations import get_specified_logging_channel
from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class MessageEvent(Cog):
    """Cog for message-related events."""

    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        logger.info(f"Message: {message}")

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        logger.info(f"Message edited: {payload}")

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        logger.info(f"Message deleted: {payload}")

    @Cog.listener()
    async def on_message_edit(
        self, before: discord.Message, after: discord.Message
    ): ...

    @Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Handle message delete events."""
        ...


async def setup(bot: Nightcore):
    """Setup the MessageEvents cog."""
    await bot.add_cog(MessageEvent(bot))
