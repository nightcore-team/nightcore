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
        # async with self.bot.uow.start() as uow:
        #     ...
        #     log_channel_id: int | None = await get_specified_logging_channel(
        #         uow.session,  # type: ignore
        #         guild_id=message.guild.id,  # type: ignore
        #         channel_type=cast(
        #             LoggingChannelType, LoggingChannelType.MESSAGES
        #         ),
        #     )

        # if log_channel_id is None:
        #     return

        # log_channel = message.guild.get_channel(log_channel_id)  # type: ignore

        # # Try to determine who deleted the message via audit logs (best-effort)
        # deleter = None
        # if message.guild and message.author and not message.author.bot:
        #     try:
        #         async for entry in message.guild.audit_logs(
        #             limit=5, action=discord.AuditLogAction.message_delete
        #         ):
        #             # Stop if entry too old.
        #             if (
        #                 discord.utils.utcnow() - entry.created_at
        #             ).total_seconds() > 5:
        #                 break
        #             # Match target (original author) and channel.
        #             if entry.target.id != message.author.id:
        #                 continue
        #             extra = entry.extra
        #             # extra.channel and extra.count exist for message_delete entries.
        #             if (
        #                 hasattr(extra, "channel")
        #                 and extra.channel.id == message.channel.id
        #                 and getattr(extra, "count", 1) == 1
        #             ):
        #                 deleter = entry.user
        #                 break
        #     except (discord.Forbidden, discord.HTTPException):
        #         pass  # Missing perms or API error; fallback to unknown.

        # if deleter is None:
        #     deleter_display = "Unknown (possibly self-deleted)"
        # else:
        #     deleter_display = f"{deleter.mention}"

        # content_preview = (
        #     (message.content[:1800] + "…")
        #     if message.content and len(message.content) > 1800
        #     else (message.content or "*No content*")
        # )

        # return await log_channel.send(  # type: ignore
        #     f"Message deleted in [#{message.channel.name}]({message.channel.jump_url}) "
        #     f"by {deleter_display} | Author: {message.author.mention}\n"
        #     f"Content: {content_preview}"
        # )


async def setup(bot: Nightcore):
    """Setup the MessageEvents cog."""
    await bot.add_cog(MessageEvent(bot))
