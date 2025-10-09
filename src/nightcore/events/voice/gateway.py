# check member`s voice state and call appropriate handlers  # noqa: D100

import logging

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildPrivateChannelsConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    get_private_room_state,
    get_specified_channel,
)
from src.nightcore.bot import Nightcore

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
        """Handle voice state update events."""
        guild = member.guild

        try:
            # user joined a voice channel

            if before.channel is None and after.channel is not None:
                async with self.bot.uow.start() as session:
                    create_private_room_channel_id = await get_specified_channel(  # noqa: E501
                        session,
                        guild_id=guild.id,
                        config_type=GuildPrivateChannelsConfig,
                        channel_type=ChannelType.CREATE_PRIVATE_VOICE_CHANNEL,
                    )
                if create_private_room_channel_id:
                    if after.channel.id == create_private_room_channel_id:
                        self.bot.dispatch(
                            "create_private_room", member, after.channel
                        )
                else:
                    self.bot.dispatch(
                        "voice_channel_join", member, before, after
                    )

                logger.info(
                    f"[voice] {member} joined voice channel {after.channel.name}"  # noqa: E501
                )

            # check if member left a voice channel
            elif before.channel is not None and after.channel is None:
                async with self.bot.uow.start() as session:
                    private_room_state = await get_private_room_state(
                        session, user_id=member.id
                    )

                if (
                    private_room_state
                    and private_room_state.channel_id == before.channel.id
                ):
                    self.bot.dispatch(
                        "delete_private_room",
                        member,
                        before.channel,
                        private_room_state,
                    )
                else:
                    self.bot.dispatch(
                        "voice_channel_leave", member, before, after
                    )

                logger.info(
                    f"[voice] {member} left voice channel {before.channel.name}"  # noqa: E501
                )

            elif (
                before.channel is not None
                and after.channel is not None
                and before.channel.id != after.channel.id
            ):
                async with self.bot.uow.start() as session:
                    private_room_state = await get_private_room_state(
                        session, user_id=member.id
                    )
                    create_private_room_channel_id = await get_specified_channel(  # noqa: E501
                        session,
                        guild_id=guild.id,
                        config_type=GuildPrivateChannelsConfig,
                        channel_type=ChannelType.CREATE_PRIVATE_VOICE_CHANNEL,
                    )

                # if user switched to create-private channel from their private
                if (
                    private_room_state
                    and create_private_room_channel_id
                    and after.channel.id == create_private_room_channel_id
                ):
                    logger.info(
                        "[voice] %s switched to create-private channel %s, moving back to %s",  # noqa: E501
                        member,
                        after.channel.name,
                        before.channel.name,
                    )
                    try:
                        await member.move_to(before.channel)
                    except Exception:
                        logger.exception(
                            "Error moving %s back to %s",
                            member,
                            before.channel.name,
                        )
                    return

                # if user switched from their private channel to another
                if (
                    private_room_state
                    and before.channel
                    and before.channel.id == private_room_state.channel_id
                    and after.channel.id != private_room_state.channel_id
                ):
                    self.bot.dispatch(
                        "delete_private_room",
                        member,
                        before.channel,
                        private_room_state,
                    )
                    logger.info(
                        "[voice] %s left their private channel %s -> %s; scheduled delete",  # noqa: E501
                        member,
                        before.channel.name,
                        after.channel.name,
                    )

                # if user switched to their private channel from another non-private  # noqa: E501
                if (
                    not private_room_state
                    and after.channel.id == create_private_room_channel_id
                ):
                    self.bot.dispatch(
                        "create_private_room", member, after.channel
                    )
                    logger.info(
                        "[voice] %s switched to create-private channel %s; scheduled create",  # noqa: E501
                        member,
                        after.channel.name,
                    )

                # if user just switched between two non-private channels
                else:
                    self.bot.dispatch(
                        "voice_channel_switch", member, before, after
                    )
                    logger.info(
                        "[voice] %s switched voice channel from %s to %s",
                        member,
                        before.channel.name,
                        after.channel.name,
                    )

        except Exception as e:
            logger.exception(
                "[voice] Failed to dispatch voice state update event: %s", e
            )


async def setup(bot: Nightcore):
    """Setup the VoiceStateUpdateEvent cog."""
    await bot.add_cog(VoiceStateUpdateEvent(bot))
