"""Check member`s voice state and call appropriate handlers."""

import logging
from typing import cast

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig, GuildPrivateChannelsConfig
from src.infra.db.models.private_rooms import PrivateRoomState
from src.infra.db.operations import (
    get_private_room_state_by_channel,
    get_specified_channel,
)
from src.nightcore.bot import Nightcore
from src.utils._enums import ChannelType

logger = logging.getLogger(__name__)


class VoiceStateUpdateEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        self.bot.dispatch("count_voice_activity", member, before, after)

        if before.channel is None and after.channel is not None:
            await self._handle_join(member, after)

        elif before.channel is not None and after.channel is None:
            await self._handle_leave(member, before)

        elif (
            before.channel is not None
            and after.channel is not None
            and before.channel.id != after.channel.id
        ):
            await self._handle_switch(member, before, after)

    async def _handle_join(
        self, member: discord.Member, after: discord.VoiceState
    ):
        guild = member.guild
        after.channel = cast(discord.VoiceChannel, after.channel)

        async with self.bot.uow.start() as session:
            create_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildPrivateChannelsConfig,
                channel_type=ChannelType.CREATE_PRIVATE_VOICE_CHANNEL,
            )
            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_VOICES,
            )

        self.bot.dispatch(
            "voice_channel_join", member, after, logging_channel_id
        )

        if create_channel_id and after.channel.id == create_channel_id:
            self.bot.dispatch("join_private_room", member, after.channel)

        logger.info("[voice/join] %s joined %s", member, after.channel.name)

    async def _handle_leave(
        self, member: discord.Member, before: discord.VoiceState
    ):
        guild = member.guild
        before.channel = cast(discord.VoiceChannel, before.channel)

        logger.info("[voice/leave] %s left %s", member, before.channel.name)

        async with self.bot.uow.start() as session:
            private_room_state = await get_private_room_state_by_channel(
                session, channel_id=before.channel.id
            )
            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_VOICES,
            )

        self.bot.dispatch(
            "voice_channel_leave", member, before, logging_channel_id
        )

        if private_room_state and len(before.channel.members) == 0:
            self.bot.dispatch(
                "delete_private_room",
                member,
                before.channel,
                private_room_state,
            )

    async def _handle_switch(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        guild = member.guild
        before.channel = cast(discord.VoiceChannel, before.channel)
        after.channel = cast(discord.VoiceChannel, after.channel)

        logger.info(
            "[voice] %s switched %s → %s",
            member,
            before.channel.name,
            after.channel.name,
        )

        async with self.bot.uow.start() as session:
            private_room_state = await get_private_room_state_by_channel(
                session, channel_id=before.channel.id
            )
            create_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildPrivateChannelsConfig,
                channel_type=ChannelType.CREATE_PRIVATE_VOICE_CHANNEL,
            )
            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_VOICES,
            )

        self.bot.dispatch(
            "voice_channel_switch", member, before, after, logging_channel_id
        )

        if not private_room_state and after.channel.id == create_channel_id:
            self.bot.dispatch("join_private_room", member, after.channel)
            logger.info(
                "[voice] %s switched to create-private %s; scheduled create",
                member,
                after.channel.name,
            )
            return

        if private_room_state:
            if (
                private_room_state.user_id == member.id
                and after.channel.id == create_channel_id
            ):
                await self._block_create_channel_entry(
                    member, before, private_room_state
                )
                return

            if len(before.channel.members) == 0:
                self.bot.dispatch(
                    "delete_private_room",
                    member,
                    before.channel,
                    private_room_state,
                )

                return

    async def _block_create_channel_entry(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        private_room_state: PrivateRoomState,
    ):

        before.channel = cast(discord.VoiceChannel, before.channel)

        logger.info(
            "[voice] %s has private room, blocking create-channel entry, moving back to %s",
            member,
            before.channel.name,
        )
        try:
            await member.move_to(before.channel)
        except Exception as e:
            logger.error(
                "Error moving %s back to %s: %s",
                member,
                before.channel.name,
                e,
            )
            self.bot.dispatch(
                "delete_private_room",
                member,
                before.channel,
                private_room_state,
            )


async def setup(bot: Nightcore):
    """Setup the VoiceStateUpdateEvent cog."""
    await bot.add_cog(VoiceStateUpdateEvent(bot))
