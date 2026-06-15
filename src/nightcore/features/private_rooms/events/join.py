# join_private_room.py — весь join-сценарий приватных комнат
"""Handle join private room events."""

import logging

import discord
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models.private_rooms import PrivateRoomState
from src.infra.db.operations import get_private_room_state_by_member
from src.nightcore.bot import Nightcore
from src.nightcore.utils import ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


class JoinPrivateRoomEvent(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_join_private_room(
        self, member: discord.Member, channel: discord.VoiceChannel
    ):
        async with self.bot.uow.start() as session:
            private_room_state = await get_private_room_state_by_member(
                session, member_id=member.id
            )

        if private_room_state:
            await self._reconnect_to_existing(
                member, private_room_state, channel
            )
        else:
            self.bot.dispatch("create_private_room", member, channel)

    async def _reconnect_to_existing(
        self,
        member: discord.Member,
        private_room_state: PrivateRoomState,
        create_room_channel: discord.VoiceChannel,
    ):
        _ch: (
            discord.VoiceChannel | None
        ) = await ensure_messageable_channel_exists(
            member.guild, private_room_state.channel_id
        )  # type: ignore
        if _ch:
            try:
                await member.move_to(_ch)
                logger.info(
                    "[voice] Moved %s to existing private room %s",
                    member,
                    _ch.name,
                )
            except Exception as e:
                logger.error(
                    "Error moving %s to private room %s: %s",
                    member,
                    _ch.name,
                    e,
                )

        else:
            await self._drop_stale_room(member, private_room_state)
            self.bot.dispatch(
                "create_private_room", member, create_room_channel
            )

    async def _drop_stale_room(
        self, member: discord.Member, private_room_state: PrivateRoomState
    ):
        async with self.bot.uow.start() as session:
            await session.delete(private_room_state)

        logger.info(
            "[voice] Stale private room %s for %s deleted, creating new one",
            private_room_state.channel_id,
            member,
        )
