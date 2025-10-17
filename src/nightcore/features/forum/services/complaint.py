"""Service for processing forum complaints."""

import logging
from typing import TYPE_CHECKING

from src.infra.api.forum.client import ForumAPIClient
from src.infra.api.forum.dto import Server, Thread
from src.infra.api.forum.utils import extract_discord_id
from src.nightcore.features.forum.components.v2 import ComplaintViewV2
from src.nightcore.features.tickets.utils import extract_str_by_pattern
from src.nightcore.utils import (
    ensure_member_exists,
    ensure_messageable_channel_exists,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

logger = logging.getLogger(__name__)


class ForumComplaintProcessor:
    def __init__(self, bot: "Nightcore", forum_api: ForumAPIClient) -> None:
        self.bot = bot
        self._api = forum_api

    async def process_server(self, server: Server) -> None:
        """Process complaints for a given server."""
        try:
            threads = await self._api.get_threads_from_section(
                server.section_id
            )
        except Exception as e:
            logger.exception(
                "[forum] Failed to fetch threads for section %s: %s",
                server.section_id,
                e,
            )
            return

        threads = self._filter_threads(threads, server.section_id)

        if not threads:
            logger.info(
                "[forum] No new complaint threads found in section %s",
                server.section_id,
            )
            return

        for thread in threads:
            await self._process_single_thread(server, thread)

    async def _process_single_thread(
        self, server: Server, thread: Thread
    ) -> None:
        """Process a single complaint thread."""
        discord_id = extract_discord_id(thread.title)  # "" якщо не знайдено
        reason = extract_str_by_pattern(thread.title, r"Причина:\s*(.+)$")

        moderator_name = "модератору"

        guild = self.bot.get_guild(server.guild_id)
        if not guild:
            logger.warning(
                "[forum] Guild with ID %s not found", server.guild_id
            )
            return

        member = await ensure_member_exists(guild, discord_id)
        if not member:
            logger.warning(
                "[forum] Member with Discord ID %s not found in guild %s",
                discord_id,
                server.guild_id,
            )

        message = (
            "[CENTER][SIZE=4][FONT=courier new]Доброго времени суток, "
            f"[USER={thread.user_id}]{thread.username}[/USER]!\n"
            "Жалоба передана [/FONT][/SIZE]"
            "[URL='https://www.youtube.com/watch?v=dQw4w9WgXcQ']"
            "[SIZE=4][FONT=courier new][COLOR=#FFFFFF][B]"
            f"{member.display_name if member else moderator_name}"
            "[/B][/COLOR][/FONT][/SIZE][/URL]\n\n"
            "[SIZE=4][FONT=courier new][COLOR=rgb(44, 130, 201)]Жалоба[/COLOR]"
            "[COLOR=rgb(239, 239, 239)] будет рассмотрена в течение [/COLOR]"
            "[COLOR=rgb(44, 130, 201)]24 часов[/COLOR]"
            "[COLOR=rgb(239, 239, 239)], ожидайте! <3[/COLOR][/FONT][/SIZE]\n"
            "[FONT=courier new]   :dream:[/FONT]\n"
            "[/CENTER]"
        )

        try:
            await self._api.create_post_in_thread(thread.thread_id, message)
        except Exception as e:
            logger.exception(
                "[forum] Failed to create post in thread %s: %s",
                thread.thread_id,
                e,
            )
            return

        try:
            await self._api.update_thread(
                thread.thread_id, prefix_id=6, sticky=1
            )
        except Exception as e:
            logger.exception(
                "[forum] Failed to update thread %s: %s", thread.thread_id, e
            )

        try:
            channel = await ensure_messageable_channel_exists(
                guild, server.channel_id
            )
            if not channel:
                logger.warning(
                    "[forum] Channel with ID %s not found in guild %s",
                    server.channel_id,
                    server.guild_id,
                )
                return

            await channel.send(  # type: ignore
                view=ComplaintViewV2(
                    self.bot,
                    url=f"{self._api.client.base_url.replace('/api', '')}{thread.url}",  # noqa: E501
                    moderator_id=discord_id if discord_id else 0,
                    ping_role_id=server.role_id,
                    reason=reason if reason else "Не указана",  # noqa: RUF001
                )
            )

        except Exception as e:
            logger.exception(
                "[forum] Failed to send Discord embed for thread %s: %s",
                thread.thread_id,
                e,
            )

    @staticmethod
    def _filter_threads(
        threads: list[Thread], section_id: int
    ) -> list[Thread]:
        return [
            t
            for t in threads
            if t.node_id == section_id and t.prefix_id == 0 and t.sticky == 0
        ]
