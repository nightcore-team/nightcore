"""Handle create private room events."""

import logging

import discord
from discord.ext.commands import Cog  # type: ignore
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from src.infra.db.models import GuildLoggingConfig, PrivateRoomState
from src.infra.db.operations import (
    get_private_room_state,
    get_specified_webhook,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.private_rooms.components.embed import (
    PrivateRoomLogEmbed,
)
from src.nightcore.utils import ensure_messageable_channel_exists
from src.nightcore.utils.webhook import send_to_webhook
from src.utils._enums import ChannelType

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

        # 1. DB-level idempotency: SELECT FOR UPDATE before any Discord I/O.
        # Prevents concurrent creates from both proceeding to channel creation.
        existing_channel_id: int | None = None
        has_existing = False
        async with self.bot.uow.start() as session:
            existing = await get_private_room_state(
                session, user_id=member.id, for_update=True
            )
            if existing is not None:
                existing_channel_id = existing.channel_id
                has_existing = True

        if has_existing and existing_channel_id is not None:
            _ch = await ensure_messageable_channel_exists(
                guild, existing_channel_id
            )
            if _ch is not None:
                try:
                    await member.move_to(_ch)  # type: ignore[arg-type]
                    logger.info(
                        "[private_rooms/event] Member %s already has "
                        "private room %s, moved back",
                        member,
                        _ch.id,  # type: ignore[attr-defined]
                    )
                except Exception as e:
                    logger.error(
                        "[private_rooms/event] Error moving %s to "
                        "existing private room %s: %s",
                        member,
                        existing_channel_id,
                        e,
                    )
                return
            # Stale DB record: channel not found, remove with lock
            async with self.bot.uow.start() as session:
                stale = await get_private_room_state(
                    session, user_id=member.id, for_update=True
                )
                if (
                    stale is not None
                    and stale.channel_id == existing_channel_id
                ):  # noqa: E501
                    await session.delete(stale)
                    logger.info(
                        "[private_rooms/event] Removed stale private room "
                        "record %s for %s",
                        existing_channel_id,
                        member,
                    )

        # 2. Create Discord channel AFTER commit (no lock held)
        try:
            private_channel = await guild.create_voice_channel(
                name=f"{member.display_name}",
                category=category,
                user_limit=channel.user_limit,
                reason="Creating private room for user",
            )
            await private_channel.set_permissions(
                member,
                overwrite=discord.PermissionOverwrite(
                    manage_channels=True,
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

        # 3. Insert with ON CONFLICT idempotency; handle orphan on race
        race_lost = False
        existing_after: PrivateRoomState | None = None
        try:
            async with self.bot.uow.start() as session:
                stmt = (
                    insert(PrivateRoomState)
                    .values(
                        guild_id=guild.id,
                        user_id=member.id,
                        channel_id=private_channel.id,
                    )
                    .on_conflict_do_nothing(index_elements=["user_id"])
                    .returning(PrivateRoomState)
                )
                result = await session.execute(stmt)
                inserted = result.scalar_one_or_none()
                if inserted is None:
                    race_lost = True
                    existing_after = await get_private_room_state(
                        session, user_id=member.id, for_update=True
                    )
        except IntegrityError as e:
            logger.warning(
                "[private_rooms/event] IntegrityError on private room "
                "insert for %s: %s",
                member,
                e,
            )
            race_lost = True
            try:
                async with self.bot.uow.start() as session:
                    existing_after = await get_private_room_state(
                        session, user_id=member.id, for_update=True
                    )
            except Exception:
                existing_after = None
        except Exception as e:
            logger.error(
                "[private_rooms/event] Error saving private room state "
                "for %s: %s",
                member,
                e,
            )
            try:
                await private_channel.delete(
                    reason="Rolling back private room creation due to DB error"
                )
            except Exception as del_e:
                logger.exception(
                    "[private_rooms/event] Error deleting private room "
                    "channel %s after DB failure: %s",
                    private_channel.id,
                    del_e,
                )
            return

        if race_lost:
            logger.info(
                "[private_rooms/event] Race: private room already exists "
                "for %s, cleaning orphan %s",
                member,
                private_channel.id,
            )
            try:
                await private_channel.delete(
                    reason="Orphan private room - race condition, "
                    "existing room present"
                )
            except Exception as e:
                logger.exception(
                    "[private_rooms/event] Error deleting orphan private "
                    "room channel %s: %s",
                    private_channel.id,
                    e,
                )
            if existing_after is not None:
                _ch = await ensure_messageable_channel_exists(
                    guild, existing_after.channel_id
                )
                if _ch is not None:
                    try:
                        await member.move_to(_ch)  # type: ignore[arg-type]
                    except Exception as e:
                        logger.error(
                            "[private_rooms/event] Error moving %s to "
                            "existing private room %s after race: %s",
                            member,
                            existing_after.channel_id,
                            e,
                        )
            return

        # 4. Move member to new channel (after successful DB insert)
        try:
            await member.move_to(private_channel)
        except Exception as e:
            logger.error(
                "[private_rooms/event] Error moving %s to private room: %s",
                member,
                e,
            )
            try:
                await private_channel.delete(
                    reason="Rolling back private room creation due to move "
                    "failure"
                )
            except Exception as del_e:
                logger.exception(
                    "[private_rooms/event] Error deleting private room "
                    "channel %s after move failure: %s",
                    private_channel.id,
                    del_e,
                )
            try:
                async with self.bot.uow.start() as session:
                    fresh = await get_private_room_state(
                        session, user_id=member.id, for_update=True
                    )
                    if (
                        fresh is not None
                        and fresh.channel_id == private_channel.id
                    ):
                        await session.delete(fresh)
            except Exception as cleanup_e:
                logger.error(
                    "[private_rooms/event] Error cleaning DB after move "
                    "failure for %s: %s",
                    member,
                    cleanup_e,
                )
            return

        # 5. Logging webhook (separate UoW, not holding private room lock)
        async with self.bot.uow.start() as session:
            log_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_PRIVATE_CHANNELS,
            )
            if log_webhook is None:
                logger.warning(
                    "[logging] Logging channel (private_rooms) not "
                    "configured for guild %s",
                    guild.id,
                )
                return

        if not log_webhook.valid:
            logger.warning(
                "[logging] Logging webhook (private_rooms) invalid for "  # noqa: E501
                "guild %s",
                guild.id,
            )
            return

        embed = PrivateRoomLogEmbed(
            title="Создание приватной комнаты",
            user_id=member.id,
            channel=private_channel,
            bot=self.bot,
        )
        await send_to_webhook(
            self.bot,
            log_webhook,
            embed,
            context="private_rooms/create",
            guild_id=guild.id,
        )


async def setup(bot: Nightcore):
    """Setup the CreatePrivateRoomEvent cog."""
    await bot.add_cog(CreatePrivateRoomEvent(bot))
