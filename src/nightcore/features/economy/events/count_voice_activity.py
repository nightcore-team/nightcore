"""Handle count user voice activity event."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord import Member, VoiceState
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import get_or_create_user

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


class CountVoiceActivityEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    async def _start_counting_voice_activity(
        self, member: Member, channel_id: int
    ) -> None:
        """Start counting voice activity for a user."""
        now = datetime.now(UTC)

        started = False
        async with self.bot.uow.start() as session:
            user, _ = await get_or_create_user(
                session,
                guild_id=member.guild.id,
                user_id=member.id,
                for_update=True,
            )

            # DB-level locking guarantees only one concurrent start wins;
            # if already counting we keep earliest start (idempotent)
            # Handle early return outside tx to ensure rollback path correct  # noqa: E501
            if user.temp_voice_activity is None:
                user.temp_voice_activity = now
                started = True
            else:
                # already counting – no modification, let tx commit empty  # noqa: E501
                # (UoW will handle commit failure without double-rollback)  # noqa: E501
                started = False

        if not started:
            return

        logger.info(
            "[voice/count] Start counting user voice %s activity in guild %s in %s",  # noqa: E501
            member.id,
            member.guild.id,
            channel_id,
        )

    async def _end_counting_voice_activity(
        self, member: Member, channel_id: int
    ) -> None:
        """End counting voice activity for a user and update their stats."""
        now = datetime.now(UTC)

        should_log = False
        async with self.bot.uow.start() as session:
            user, _ = await get_or_create_user(
                session,
                guild_id=member.guild.id,
                user_id=member.id,
                for_update=True,
            )

            # If not currently counting, skip – handle early return outside tx  # noqa: E501
            if user.temp_voice_activity is None:
                should_log = False
            else:
                total_seconds = (  # noqa: E501
                    (now - user.temp_voice_activity).total_seconds()
                )

                user.voice_activity += int(total_seconds)
                user.temp_voice_activity = None
                should_log = True

        if not should_log:
            return

        logger.info(
            "[voice/count] Stop counting user voice %s activity in guild %s in %s",  # noqa: E501
            member.id,
            member.guild.id,
            channel_id,
        )

    @Cog.listener()
    async def on_count_voice_activity(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        """Count voice activity for users."""

        guild = member.guild

        # join
        if (
            before.channel is None
            and after.channel is not None
            and after.channel != guild.afk_channel
        ):
            await self._start_counting_voice_activity(member, after.channel.id)

        # leave
        elif before.channel is not None and after.channel is None:
            await self._end_counting_voice_activity(member, before.channel.id)

        # switch
        elif (
            before.channel is not None
            and after.channel is not None
            and before.channel.id != after.channel.id
        ):
            if after.channel == guild.afk_channel:
                await self._end_counting_voice_activity(
                    member, before.channel.id
                )
            elif (
                before.channel == guild.afk_channel
                and after.channel != guild.afk_channel
            ):
                await self._start_counting_voice_activity(
                    member, after.channel.id
                )
            else:
                # continue counting
                return

        logger.info(
            "[%s/log] - invoked user=%s guild=%s",
            "economy/levelup",
            member.id,
            guild.id,
        )


async def setup(bot: "Nightcore"):
    """Setup the CountVoiceActivityEvent cog."""
    await bot.add_cog(CountVoiceActivityEvent(bot))
