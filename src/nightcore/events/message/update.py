"""Handle message update events."""

import io
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

import discord
from discord import Message
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (  # type: ignore
    get_specified_channel,
    get_specified_field,
)
from src.nightcore.utils import ensure_messageable_channel_exists

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class UpdateMessageEvent(Cog):
    def __init__(self, bot: "Nightcore"):
        self.bot = bot

    def _check_symbols_sum(
        self, parts: list[str], embed: discord.Embed
    ) -> bool:
        total = 0
        for p in parts:
            total += len(p or "")

        for f in embed.fields:
            total += len(f.name or "")
            total += len(f.value or "")

        if embed.author:
            total += len(embed.author.name or "")
        if embed.footer:
            total += len(embed.footer.text or "")

        return total > 6000

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        """Handle message update events."""

        guild = after.guild

        if not guild:
            logger.error(
                "[message] Updated message is not from a guild: %s", after
            )
            return

        async with self.bot.uow.start() as session:
            if not (
                logging_channel_id := await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_MESSAGES,
                )
            ):
                logger.error(
                    "[message] No logging channel configured for guild %s",
                    guild.id,
                )
                return

            ignoring_channels_ids = cast(
                list[int],
                await get_specified_field(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    field_name="message_log_ignoring_channels_ids",
                ),
            )

        if ignoring_channels_ids:
            if after.channel.id in ignoring_channels_ids:
                logger.info(
                    "[message] Message can't be deleted from ignored channel %s in guild %s",  # noqa: E501
                    after.channel.id,
                    guild.id,
                )
                return
        else:
            logger.error(
                "[message] No ignoring channels configured for guild %s",
                guild.id,
            )

        channel = await ensure_messageable_channel_exists(
            guild=guild, channel_id=logging_channel_id
        )
        if not channel:
            logger.error(
                "[message] Logging channel %s not found in guild %s",
                logging_channel_id,
                guild.id,
            )
            return

        author = after.author or before.author
        if not author or author.bot:
            return

        old_content = before.content if before else "не найдено"
        old_attachments = before.attachments if before else []

        embed = discord.Embed(
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_author(name="Сообщение было изменено")

        embed.set_footer(
            text="Powered by nightcore",
            icon_url=self.bot.user.display_avatar.url,  # type: ignore
        )

        # check if we need to convert to file
        convert_text_to_file = self._check_symbols_sum(
            [old_content or "", after.content or "", embed.title or ""], embed
        )

        files: list[discord.File] = []

        # old attachments
        if old_attachments:
            result = ""
            for attachment in old_attachments:
                url = attachment.url
                proxy_url = getattr(attachment, "proxy_url", None) or url
                result += f"[URL](<{url}>) | [PROXY_URL](<{proxy_url}>)\n"

            if len(result) > 1024 or convert_text_to_file:
                files.append(
                    discord.File(
                        io.BytesIO(result.encode("utf-8")),
                        filename=f"{after.id}_beforeUpdateAttachments.txt",
                    )
                )
            else:
                embed.add_field(
                    name="Старые вложения", value=result, inline=False
                )

        # new attachments
        if after.attachments:
            result = ""
            for attachment in after.attachments:
                url = attachment.url
                proxy_url = getattr(attachment, "proxy_url", None) or url
                result += f"[URL](<{url}>) | [PROXY_URL](<{proxy_url}>)\n"

            if len(result) > 1024 or convert_text_to_file:
                files.append(
                    discord.File(
                        io.BytesIO(result.encode("utf-8")),
                        filename=f"{after.id}_afterUpdateAttachments.txt",
                    )
                )
            else:
                embed.add_field(
                    name="Новые вложения", value=result, inline=False
                )

        # content
        if (old_content or "") != (after.content or ""):
            # old content
            if old_content:
                if len(old_content) > 1024 or convert_text_to_file:
                    files.append(
                        discord.File(
                            io.BytesIO((old_content or "").encode("utf-8")),
                            filename=f"{after.id}_beforeUpdateContent.txt",
                        )
                    )
                else:
                    embed.add_field(
                        name="Старое содержимое:",
                        value=old_content,
                        inline=False,
                    )

            # new content
            new_content = after.content or ""
            if new_content:
                if len(new_content) > 1024 or convert_text_to_file:
                    files.append(
                        discord.File(
                            io.BytesIO(new_content.encode("utf-8")),
                            filename=f"{after.id}_afterUpdateContent.txt",
                        )
                    )
                else:
                    embed.add_field(
                        name="Новое содержимое:",
                        value=new_content,
                        inline=False,
                    )

        embed.add_field(name="Автор:", value=author.mention, inline=True)
        if channel:
            embed.add_field(name="Канал:", value=channel.mention, inline=True)

        if len(files) == 0 and len(embed.fields) <= 2:
            return

        try:
            await channel.send(embed=embed, files=files)  # type: ignore
        except Exception as e:
            logger.error(
                "[message] Failed to send deleted message log to channel %s in guild %s: %s",  # noqa: E501
                channel.id,
                guild.id,
                e,
            )

        logger.info(
            "[message] Message updated: Old - %s, New - %s",
            before,
            after,
        )

        return


async def setup(bot: "Nightcore") -> None:
    """Setup the UpdateMessageEvent cog."""
    await bot.add_cog(UpdateMessageEvent(bot))
