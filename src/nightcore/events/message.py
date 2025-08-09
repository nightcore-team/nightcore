"""Message events module."""

from typing import cast

import discord
from discord.ext.commands import Cog

from src.infra.db.models.enums import LoggingChannelType
from src.infra.db.operations import get_specified_logging_channel
from src.nightcore.bot import Nightcore


class MessageEvents(Cog):
    """Cog for message-related events."""

    def __init__(self, bot: Nightcore):
        self.bot = bot

    @Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: discord.User
    ):
        async with self.bot.uow.start() as uow:
            log_channel_id: int | None = await get_specified_logging_channel(
                uow.session,  # type: ignore
                guild_id=reaction.message.guild.id,  # type: ignore
                channel_type=cast(
                    LoggingChannelType, LoggingChannelType.REACTIONS
                ),
            )

        if log_channel_id is None:
            return  # channel not found / no permission

        log_channel = reaction.message.guild.get_channel(log_channel_id)  # type: ignore

        return await log_channel.send(  # type: ignore
            f"{user.display_name} reacted to [message]({reaction.message.jump_url}) with {reaction.emoji}"
        )


async def setup(bot: Nightcore):
    """Setup the MessageEvents cog."""
    await bot.add_cog(MessageEvents(bot))
