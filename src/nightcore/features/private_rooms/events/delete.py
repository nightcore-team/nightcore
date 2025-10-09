# remove private room with name of username on leave
# send log message to logging channel
# delete temp record from database
"""Handle delete private room events."""

import logging

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig, PrivateRoomState
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import get_specified_channel
from src.nightcore.bot import Nightcore
from src.nightcore.features.private_rooms.components.embed import (
    PrivateRoomLogEmbed,
)
from src.nightcore.utils import ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


class DeletePrivateRoomEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_delete_private_room(
        self,
        member: discord.Member,
        channel: discord.VoiceChannel,
        private_room_state: PrivateRoomState,
    ):
        """Handle delete private room events."""
        guild = member.guild

        try:
            await channel.delete(reason="Deleting private room on user leave")

        except Exception as e:
            logger.error(f"Error deleting private room for {member}: {e}")
            return

        try:
            async with self.bot.uow.start() as session:
                await session.delete(private_room_state)

                optional_log_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_PRIVATE_CHANNELS,
                )
                if optional_log_channel_id is None:
                    logger.warning(
                        f"[logging] Logging channel (private_rooms) not configured for guild {guild.id}"  # noqa: E501
                    )
                    return

                log_channel_id = optional_log_channel_id

        except Exception as e:
            logger.error(
                f"Error deleting private room record for {member}: {e}"
            )
            return

        if not (
            log_channel := await ensure_messageable_channel_exists(
                guild, log_channel_id
            )
        ):
            logger.warning(
                f"[logging] Logging channel (private_rooms) not configured for guild {guild.id}"  # noqa: E501
            )
            return

        try:
            embed = PrivateRoomLogEmbed(
                title="Удаление приватной комнаты",
                user_id=member.id,
                channel=channel,
                bot=self.bot,
            )
            await log_channel.send(embed=embed)  # type: ignore
        except Exception as e:
            logger.error(
                f"Error sending log message for private room of {member}: {e}"
            )
            return


async def setup(bot: Nightcore):
    """Setup the DeletePrivateRoomEvent cog."""
    await bot.add_cog(DeletePrivateRoomEvent(bot))
