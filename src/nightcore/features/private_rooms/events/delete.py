"""Handle delete private room events."""

import logging

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig, PrivateRoomState
from src.infra.db.operations import get_specified_webhook
from src.nightcore.bot import Nightcore
from src.nightcore.features.private_rooms.components.embed import (
    PrivateRoomLogEmbed,
)
from src.nightcore.utils.webhook import send_to_webhook
from src.utils._enums import ChannelType

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
        except discord.NotFound as e:
            logger.error(
                "[private_rooms/event] Private room channel not found for %s: %s",  # noqa: E501
                member,
                e,
            )
        except Exception as e:
            logger.error(
                "[private_rooms/event] Error deleting private room for %s: %s",
                member,
                e,
            )
            return

        try:
            async with self.bot.uow.start() as session:
                await session.delete(private_room_state)

                log_webhook = await get_specified_webhook(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_PRIVATE_CHANNELS,
                )
                if log_webhook is None:
                    logger.warning(
                        f"[logging] Logging channel (private_rooms) not configured for guild {guild.id}"  # noqa: E501
                    )
                    return

        except Exception as e:
            logger.error(
                "[private_rooms/event] Error deleting private room record for %s: %s",  # noqa: E501
                member,
                e,
            )
            return

        if not log_webhook.valid:
            logger.warning(
                f"[logging] Logging webhook (private_rooms) invalid for guild {guild.id}"  # noqa: E501
            )
            return

        embed = PrivateRoomLogEmbed(
            title="Удаление приватной комнаты",
            user_id=member.id,
            channel=channel,
            bot=self.bot,
        )
        await send_to_webhook(
            self.bot,
            log_webhook,
            embed,
            context="private_rooms/delete",
            guild_id=guild.id,
        )


async def setup(bot: Nightcore):
    """Setup the DeletePrivateRoomEvent cog."""
    await bot.add_cog(DeletePrivateRoomEvent(bot))
