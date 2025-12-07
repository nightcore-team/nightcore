"""Handle create private room events."""

import asyncio
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


class CreatePrivateRoomEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_create_private_room(
        self,
        member: discord.Member,
        channel: discord.VoiceChannel,
    ):
        """Handle create private room events."""
        guild = member.guild

        category = channel.category

        try:
            channel = await guild.create_voice_channel(
                name=f"{member.display_name}",
                category=category,
                user_limit=channel.user_limit,
                reason="Creating private room for user",
            )
            await channel.set_permissions(
                member,
                overwrite=discord.PermissionOverwrite(
                    manage_channels=True,
                    manage_permissions=True,
                    view_channel=True,
                    connect=True,
                    speak=True,
                    mute_members=True,
                    deafen_members=True,
                    move_members=True,
                ),
            )

        except Exception as e:
            logger.error(
                "[private_rooms/event] Error creating private room for %s: %s",
                member,
                e,
            )
            return

        try:
            async with self.bot.uow.start() as session:
                private_room = PrivateRoomState(
                    guild_id=guild.id,
                    user_id=member.id,
                    channel_id=channel.id,
                )
                session.add(private_room)
                await session.flush()
        except Exception as e:
            logger.error(
                "[private_rooms/event] Error saving private room state for %s: %s",  # noqa: E501
                member,
                e,
            )
            try:
                asyncio.create_task(
                    channel.delete(
                        reason="Rolling back private room creation due to DB error"  # noqa: E501
                    )
                )
            except Exception as delete_error:
                logger.exception(
                    "[private_rooms/event] Error deleting private room channel %s after DB failure: %s",  # noqa: E501
                    channel.id,
                    delete_error,
                )

        try:
            await member.move_to(channel)
        except Exception as e:
            logger.error(
                "[private_rooms/event] Error moving %s to private room: %s",
                member,
                e,
            )
            return

        async with self.bot.uow.start() as session:
            optional_log_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_PRIVATE_CHANNELS,
            )
            if optional_log_channel_id is None:
                logger.warning(
                    "[logging] Logging channel (private_rooms) not configured for guild %s",  # noqa: E501
                )
                return
            log_channel_id = optional_log_channel_id

        if not (
            log_channel := await ensure_messageable_channel_exists(
                guild, log_channel_id
            )
        ):
            logger.warning(
                "[logging] Logging channel (private_rooms) not configured for guild %s",  # noqa: E501
                guild.id,
            )
            return

        try:
            embed = PrivateRoomLogEmbed(
                title="Создание приватной комнаты",
                user_id=member.id,
                channel=channel,
                bot=self.bot,
            )
            await log_channel.send(embed=embed)  # type: ignore
        except Exception as e:
            logger.error(
                "[private_rooms/event] Error sending log message for private room of %s: %s",  # noqa: E501
                member,
                e,
            )
            return


async def setup(bot: Nightcore):
    """Setup the CreatePrivateRoomEvent cog."""
    await bot.add_cog(CreatePrivateRoomEvent(bot))
