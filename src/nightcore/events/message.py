"""Message events module."""

import logging

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import MainGuildConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_specified_channel

# from discord.raw_models import RawMessageDeleteEvent, RawMessageUpdateEvent
from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class MessageEvent(Cog):
    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle message create events."""
        guild = message.guild
        # TODO: separate all logic to different events
        if not guild:
            if not message.attachments:
                return
            # TODO: fix it -> user will get reply from bot anytime he sends 2 attachments in DM  # noqa: E501
            if len(message.attachments) > 1:
                try:
                    return await message.reply(
                        "Пожалуйста, отправляйте только один скриншот вашей статистики.",  # noqa: E501
                        mention_author=True,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to reply to user %s in DM: %s",
                        message.author.id,
                        e,
                    )
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

    # @Cog.listener()
    # async def on_raw_message_edit(
    #     self, payload: RawMessageUpdateEvent
    # ): ...  # logger.info(f"Message edited: {payload}")

    # @Cog.listener()
    # async def on_raw_message_delete(
    #     self, payload: RawMessageDeleteEvent
    # ): ...  # logger.info(f"Message deleted: {payload}")

    # @Cog.listener()
    # async def on_message_edit(
    #     self, before: discord.Message, after: discord.Message
    # ): ...

    @Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Handle message delete events."""
        ...


async def setup(bot: Nightcore):
    """Setup the MessageEvents cog."""
    await bot.add_cog(MessageEvent(bot))
