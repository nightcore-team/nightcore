"""Service for processing forum complaints."""

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from nightforo import (
    Client as XenforoClient,
)
from nightforo import (
    PostCreateParams,
    Thread,
    ThreadsGetParams,
    ThreadUpdateParams,
)

from src.infra.api.forum.utils import extract_discord_id
from src.infra.db.models.guild import GuildForumConfig
from src.infra.db.operations import (
    get_or_create_processed_thread,
)
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
    def __init__(self, bot: "Nightcore", forum_api: XenforoClient) -> None:
        self.bot = bot
        self._api = forum_api

    async def process_servers(
        self, servers: Sequence[GuildForumConfig]
    ) -> None:
        """Process complaints for a given server."""
        logger.info(
            "[forum] Starting complaint processing",
        )
        try:
            threads_resp = await self._api.get_threads(
                ThreadsGetParams(prefix_id=0)
            )
            logger.info(
                "[forum] Fetched %s total threads from API",
                len(threads_resp.threads),
            )
        except Exception as e:
            logger.exception(
                "[forum] Failed to fetch threads: %s",
                e,
            )
            return

        filtered_threads = self._filter_threads(threads_resp.threads, servers)
        logger.info(
            "[forum] After filtering: %s complaint threads to process (prefix_id=0, sticky=0)",  # noqa: E501
            len(filtered_threads),
        )

        if not filtered_threads:
            logger.info(
                "[forum] No new complaint threads found",
            )
            return

        for config, threads in filtered_threads.items():
            for thread in threads:
                async with self.bot.uow.start() as session:
                    processed_thread = await get_or_create_processed_thread(
                        session, thread_id=thread.thread_id
                    )

                if processed_thread is not None:
                    continue

                await self._process_single_thread(config, thread)

    async def _process_single_thread(
        self, server: GuildForumConfig, thread: Thread
    ) -> None:
        """Process a single complaint thread."""
        logger.info(
            "[forum] Processing thread_id=%s, node_id=%s, prefix_id=%s, sticky=%s, title='%s', url=%s",  # noqa: E501
            thread.thread_id,
            thread.node_id,
            thread.prefix_id,
            thread.sticky,
            thread.title,
            thread.view_url,
        )
        discord_id = extract_discord_id(thread.title)
        reason = extract_str_by_pattern(thread.title, r"Причина:\s*(.+)$")
        logger.info(
            "[forum] Extracted from thread %s: discord_id=%s, reason='%s'",
            thread.thread_id,
            discord_id,
            reason,
        )

        moderator_name = "модератору"

        guild = self.bot.get_guild(server.guild_id)
        if not guild:
            logger.info("[forum] Guild with ID %s not found", server.guild_id)
            return

        member = await ensure_member_exists(guild, discord_id)
        if not member:
            logger.info(
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

        logger.info(
            "[forum] Prepared post data for thread %s: thread_id=%s (type=%s), message_length=%s",  # noqa: E501
            thread.thread_id,
            thread.thread_id,
            type(thread.thread_id).__name__,
            len(message) if message else 0,
        )

        post_create_params = PostCreateParams(
            thread_id=thread.thread_id, message=message
        )

        logger.info(
            "[forum] PostCreateParams created: thread_id=%s, message=%s, dict=%s",  # noqa: E501
            post_create_params.thread_id,
            post_create_params.message[:100]
            if post_create_params.message
            else None,
            post_create_params.model_dump(exclude_none=True),
        )

        try:
            response = await self._api.create_post(post_create_params)
            logger.info(
                "[forum] Successfully created post in thread %s %s",
                thread.thread_id,
                str(response),
            )
        except Exception as e:
            logger.exception(
                "[forum] Failed to create post in thread %s: %s",
                thread.thread_id,
                e,
            )
            return

        update_thread_params = ThreadUpdateParams(
            prefix_id=6,
            sticky=True,
        )

        try:
            await self._api.update_thread(
                thread.thread_id, update_thread_params
            )
            logger.info(
                "[forum] Successfully updated thread %s (prefix_id=6, sticky=True)",  # noqa: E501
                thread.thread_id,
            )
        except Exception as e:
            logger.exception(
                "[forum] Failed to update thread %s: %s", thread.thread_id, e
            )
            return

        try:
            channel = await ensure_messageable_channel_exists(
                guild, server.channel_id
            )
            if not channel:
                logger.info(
                    "[forum] Channel with ID %s not found in guild %s",
                    server.channel_id,
                    server.guild_id,
                )
                return

            await channel.send(  # type: ignore
                view=ComplaintViewV2(
                    self.bot,
                    url=thread.view_url if thread.view_url else "",
                    moderator_id=discord_id if discord_id else 0,
                    ping_role_id=server.role_id,
                    reason=reason if reason else "Не указана",
                )
            )
            logger.info(
                "[forum] Successfully sent Discord message for thread %s to channel %s",  # noqa: E501
                thread.thread_id,
                server.channel_id,
            )

        except Exception as e:
            logger.exception(
                "[forum] Failed to send Discord embed for thread %s: %s",
                thread.thread_id,
                e,
            )

    @staticmethod
    def _filter_threads(
        threads: list[Thread], servers: Sequence[GuildForumConfig]
    ) -> dict[GuildForumConfig, list[Thread]]:
        result: dict[GuildForumConfig, list[Thread]] = {}

        for config in servers:
            result[config] = [
                t
                for t in threads
                if t.node_id == config.section_id
                and t.prefix_id == 0
                and t.sticky == 0
            ]

        return result
