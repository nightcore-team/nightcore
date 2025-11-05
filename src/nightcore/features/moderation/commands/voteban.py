"""Command to send a vote ban request."""

import logging
from typing import TYPE_CHECKING, cast

from discord import (
    Guild,
    Member,
    User,
    app_commands,
)
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

from src.config.config import config
from src.infra.db.models import GuildModerationConfig
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.moderation.components.v2 import (
    BanRequestViewV2,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import (
    compare_top_roles,
    ensure_member_exists,
    ensure_messageable_channel_exists,
    ensure_role_exists,
    has_any_role_from_sequence,
)
from src.nightcore.utils.time_utils import parse_duration

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class Voteban(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

    @app_commands.command(
        name="voteban",
        description="Отправить запрос на голосование по бану пользователя",
    )
    @app_commands.describe(
        user="Пользователь, которого нужно забанить",
        reason="Причина бана пользователя",
        duration="Продолжительность бана (например, 1h, 1d, 7d)",
        delete_messages_per="Удалять сообщения за последний период времени (например, 1h, 1d, 7d)",  # noqa: E501
        # proofs="Собрать доказательства для запроса на бан",
    )
    async def voteban(
        self,
        interaction: Interaction,
        user: User,
        duration: str,
        reason: str,
        delete_messages_per: str | None = None,
        # proofs: bool = False,
    ):
        """Vote to ban a user on the server."""
        guild = cast(Guild, interaction.guild)
        # proofs = False

        # Ensure we have a guild Member object
        member = await ensure_member_exists(guild, user.id)

        if member is None:
            return await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "пользователь",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        ping_role = None

        async with specified_guild_config(
            self.bot,
            guild.id,
            GuildModerationConfig,
            _create=False,
        ) as (guild_config, _):
            if not (
                moderation_access_roles
                := guild_config.moderation_access_roles_ids
            ):
                raise FieldNotConfiguredError("доступ к модерации")

            if not (ban_access_roles := guild_config.ban_access_roles_ids):
                raise FieldNotConfiguredError("доступ к банам")

            if not (
                ban_request_channel_id
                := guild_config.send_ban_request_channel_id
            ):
                raise FieldNotConfiguredError("канал запросов на бан")

            ping_role_id = guild_config.ban_request_ping_role_id

        if ping_role_id:
            ping_role = await ensure_role_exists(guild, ping_role_id)

        has_moder_role = has_any_role_from_sequence(
            cast(Member, interaction.user), moderation_access_roles
        )

        if not has_moder_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        is_member_moderator = has_any_role_from_sequence(
            member, moderation_access_roles
        )
        if is_member_moderator:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете забанить модераторов.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if member.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете забанить администраторов.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if guild.me == member:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Вы не можете забанить меня.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not compare_top_roles(guild, member):
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "Я не могу забанить этого пользователя, потому что у него роль выше, чем у меня.",  # noqa: E501
                ),
                ephemeral=True,
            )

        parsed_duration = parse_duration(duration)

        if not parsed_duration:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Неверная продолжительность. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        parsed_delete_messages_per_seconds = 0

        if delete_messages_per:
            tmp_delete_messages_per = parse_duration(delete_messages_per)

            if tmp_delete_messages_per is None:
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        "Неверная продолжительность удаления сообщений. Используйте s/m/h/d (например, 1h, 1d, 7d).",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            if tmp_delete_messages_per > config.bot.DELETE_MESSAGES_SECONDS:
                return await interaction.response.send_message(
                    embed=ValidationErrorEmbed(
                        f"Продолжительность удаления сообщений не может превышать {config.bot.DELETE_MESSAGES_SECONDS // 86400} дней.",  # noqa: E501
                        self.bot.user.name,  # type: ignore
                        self.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            parsed_delete_messages_per_seconds = tmp_delete_messages_per

        channel = await ensure_messageable_channel_exists(
            guild, ban_request_channel_id
        )
        if not channel:
            return await interaction.response.send_message(
                embed=EntityNotFoundEmbed(
                    "канал",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
        await interaction.response.defer(thinking=True, ephemeral=True)

        # collected_files: list[File] = []
        # # attachments_by_msg: dict[
        #     int, list[discord.Attachment]
        # ] = {}  # msg_id -> attachments kept (<= 7)
        # messages_by_id: dict[
        #     int, discord.Message
        # ] = {}  # msg_id -> Message (for later cleanup)
        # if proofs:
        #     # Ephemeral control panel to finish/cancel the evidence collection  # noqa: E501
        #     acview = AttachmentsCollectorV2(
        #         author_id=interaction.user.id, user=member, bot=self.bot
        #     )

        #     await interaction.followup.send(
        #         view=acview,
        #         ephemeral=True,
        #     )

        #     lock = asyncio.Lock()
        #     # Evidence collection with deletion tracking

        #     def total_count() -> int:
        #         return sum(len(v) for v in attachments_by_msg.values())

        #     def msg_check(message: discord.Message) -> bool:
        #         if message.author.id != interaction.user.id:
        #             return False
        #         if message.channel.id != interaction.channel_id:
        #             return False
        #         if not message.attachments:
        #             return False
        #         return True

        #     async def add_message(msg: discord.Message) -> None:
        #         # keep only image attachments; expand if you want videos/docs as well  # noqa: E501
        #         imgs: list[discord.Attachment] = []
        #         for a in msg.attachments:
        #             ct = (a.content_type or "").lower()
        #             if ct.startswith("image/") or a.filename.lower().endswith(  # noqa: E501
        #                 (".png", ".jpg", ".jpeg", ".gif", ".webp")
        #             ):
        #                 imgs.append(a)
        #         if not imgs:
        #             return
        #         async with lock:
        #             remain = (
        #                 config.bot.VOTEBAN_ATTACHMENTS_LIMIT - total_count()
        #             )
        #             if remain <= 0:
        #                 return
        #             messages_by_id[msg.id] = msg
        #             attachments_by_msg[msg.id] = imgs[:remain]
        #             if total_count() >= config.bot.VOTEBAN_ATTACHMENTS_LIMIT:
        #                 acview.done.set()

        #     async def listener():
        #         while not acview.done.is_set():
        #             try:
        #                 msg = await self.bot.wait_for(
        #                     "message", timeout=1.0, check=msg_check
        #                 )
        #             except asyncio.TimeoutError:
        #                 continue
        #             except Exception:
        #                 continue
        #             with contextlib.suppress(Exception):
        #                 await add_message(msg)

        #     async def deletion_watcher():
        #         # track deletions to remove evidence if user deletes message(s)  # noqa: E501
        #         while not acview.done.is_set():
        #             done, pending = await asyncio.wait(
        #                 [
        #                     asyncio.create_task(
        #                         self.bot.wait_for(
        #                             "raw_message_delete", timeout=1.0
        #                         )
        #                     ),
        #                     asyncio.create_task(
        #                         self.bot.wait_for(
        #                             "raw_bulk_message_delete", timeout=1.0
        #                         )
        #                     ),
        #                 ],
        #                 return_when=asyncio.FIRST_COMPLETED,
        #             )
        #             for t in done:
        #                 try:
        #                     payload = t.result()
        #                 except asyncio.TimeoutError:
        #                     continue
        #                 except Exception:
        #                     continue

        #                 # single delete
        #                 if isinstance(payload, discord.RawMessageDeleteEvent):  # noqa: E501
        #                     if (
        #                         payload.channel_id != interaction.channel_id
        #                         or payload.guild_id != interaction.guild_id
        #                     ):
        #                         continue
        #                     mid = payload.message_id
        #                     async with lock:
        #                         attachments_by_msg.pop(mid, None)
        #                         messages_by_id.pop(mid, None)

        #             for p in pending:
        #                 p.cancel()
        #                 with contextlib.suppress(asyncio.CancelledError):
        #                     await p

        #     listener_task = asyncio.create_task(listener())
        #     delete_task = asyncio.create_task(deletion_watcher())

        #     try:
        #         await acview.done.wait()
        #     finally:
        #         for t in (listener_task, delete_task):
        #             t.cancel()
        #             with contextlib.suppress(asyncio.CancelledError):
        #                 await t

        #     if acview.cancelled:
        #         await interaction.followup.send(
        #             "Сбор отменён. Запрос не создан.",  # noqa: RUF003
        #             ephemeral=True,
        #         )
        #         return

        #     # Convert remaining (non-deleted) evidence to File just before sending  # noqa: E501
        #     for _, atts in list(attachments_by_msg.items()):
        #         for att in atts:
        #             try:
        #                 f = await att.to_file()
        #             except Exception:
        #                 continue
        #             collected_files.append(f)
        #             if (
        #                 len(collected_files)
        #                 >= config.bot.VOTEBAN_ATTACHMENTS_LIMIT
        #             ):
        #                 break
        #         if (
        #             len(collected_files)
        #             >= config.bot.VOTEBAN_ATTACHMENTS_LIMIT
        #         ):
        #             break

        # Build and send the ban request with gallery (files=...) and the interactive view  # noqa: E501
        view = BanRequestViewV2(
            author_id=interaction.user.id,
            reason=reason,
            target=user,
            bot=self.bot,
            ping_role=ping_role,
            original_duration=duration,
            duration=parsed_duration,
            original_delete_seconds=delete_messages_per,
            delete_seconds=parsed_delete_messages_per_seconds,
            ban_access_roles_ids=ban_access_roles,
            moderation_access_roles_ids=moderation_access_roles,
        )

        try:
            message = await channel.send(  # type: ignore
                view=view
            )

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Запрос на бан отправлен",
                    f"Ваш {message.jump_url} для {user.mention} был успешно отправлен.",  # noqa: E501 # type: ignore
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
            )

        except Exception as e:
            logger.exception(
                "Failed to send message in guild %s to channel %s: %s",
                channel.guild.id,
                channel.id,
                e,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка отправки запроса на бан",
                    "Не удалось отправить сообщение с запросом на бан.",
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                )
            )

        # Cleanup: remove user's evidence messages from the channel to avoid clutter  # noqa: E501
        # if proofs:
        #     ch = interaction.channel
        #     if isinstance(ch, discord.TextChannel):
        #         # Collect messages that still exist and belong to this channel  # noqa: E501
        #         msgs_to_delete = [
        #             m
        #             for m in messages_by_id.values()
        #             if m and m.channel.id == ch.id
        #         ]
        #         if msgs_to_delete:
        #             now = discord.utils.utcnow()
        #             recent: list[discord.Message] = []
        #             old: list[discord.Message] = []

        #             for m in msgs_to_delete:
        #                 if (now - m.created_at).days < 14:
        #                     recent.append(m)
        #                 else:
        #                     old.append(m)

        #             if recent:
        #                 with contextlib.suppress(
        #                     discord.Forbidden, discord.HTTPException
        #                 ):
        #                     await ch.delete_messages(recent)

        #             for m in old:
        #                 with contextlib.suppress(
        #                     discord.Forbidden, discord.HTTPException
        #                 ):
        #                     await m.delete()

        logger.info(
            "[ban_request_submit] - invoked user=%s guild=%s target=%s duration=%s reason=%s delete_messages_for_last=%s",  # noqa: E501
            interaction.user.id,
            channel.guild.id,
            user.id,
            duration,
            reason,
            delete_messages_per,
        )


async def setup(bot: "Nightcore") -> None:
    """Setup the Voteban cog."""
    await bot.add_cog(Voteban(bot))
