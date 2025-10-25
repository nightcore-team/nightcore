"""Nightcore Bot."""

import asyncio
import contextlib
import logging
from collections.abc import Awaitable
from datetime import datetime, timezone

import discord
from discord import Guild, app_commands
from discord.ext.commands import Bot  # type: ignore

from src.config.config import config
from src.infra.api.forum.client import ForumAPIClient
from src.infra.api.httpx_client import HttpxAPIClient
from src.infra.db.uow import UnitOfWork
from src.nightcore.features.clans.components.v2 import ClanShopViewV2
from src.nightcore.features.moderation.components.v2 import (
    NotifyViewV2,
)
from src.nightcore.features.proposals.components.v2 import ProposalViewV2
from src.nightcore.features.role_requests.components.v2 import (
    CheckRoleRequestView,
    SendRoleRequestView,
)
from src.nightcore.features.tickets.components.v2 import (
    CreateTicketViewV2,
    ManageTicketViewV2,
)
from src.nightcore.utils import log_tree_summary

logger = logging.getLogger(__name__)


class CustomAPICollection:
    def __init__(self, http_client: HttpxAPIClient):
        self.http_client = http_client

    @property
    def forum(self) -> ForumAPIClient:
        """Get the Forum API client."""
        return ForumAPIClient(self.http_client)


class GuildOnlyTree(app_commands.CommandTree):
    async def interaction_check(
        self, interaction: discord.Interaction
    ) -> bool:
        """Check if the interaction is from a guild."""
        if interaction.guild is None:
            with contextlib.suppress(discord.InteractionResponded):
                await interaction.response.send_message(
                    "Commands are only available in servers.",
                    ephemeral=True,
                )
            return False
        return True


class Nightcore(Bot):
    def __init__(
        self,
        *,
        cog_modules: list[str],
        uow: UnitOfWork,
    ):
        self.cog_modules = cog_modules
        self.uow = uow
        self.outside_http_client = HttpxAPIClient(
            base_url=config.forum.FORUM_API_URL,
            default_headers={
                "XF-Api-Key": config.forum.FORUM_API_KEY,
            },
        )
        self.apis = CustomAPICollection(self.outside_http_client)

        # custom tcp connector
        # connector = TCPConnector(
        #     limit=0, ttl_dns_cache=300, enable_cleanup_closed=True
        # )
        super().__init__(
            command_prefix=".",
            intents=discord.Intents.all(),
            help_command=None,
            tree_cls=GuildOnlyTree,
            # connector=connector,
            chunk_guilds_at_startup=True,
        )
        self.chunked_guilds: int = 0
        self.startup_time: datetime = datetime.now(timezone.utc)

    async def _warmup_discord(self) -> None:
        try:
            await self.application_info()
        except Exception as e:
            logger.error(f"[failed] Warmup failed: {e}")

        tasks: list[Awaitable[None]] = []

        for guild in self.guilds:
            tasks.append(self._warmup_guild_channels(guild))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _warmup_guild_channels(self, guild: Guild) -> None:
        try:
            await guild.fetch_channels()
        except Exception as e:
            logger.error(
                f"[failed] Failed to fetch channels for guild {guild.id}: {e}"
            )
            return

    async def init_views(self) -> None:
        """Initialize persistent views."""

        views: list[discord.ui.LayoutView] = [
            CreateTicketViewV2(self),
            ClanShopViewV2(self, _build=True),
            ManageTicketViewV2(self),
            CheckRoleRequestView(self),
            SendRoleRequestView(self),
            NotifyViewV2(self, _build=True),
            ProposalViewV2(self, _build=True),
        ]

        for view in views:
            logger.info("Loading persistent view: %s", view.__class__.__name__)
            self.add_view(view)

    async def load_extensions(self) -> None:
        """Load all bot extensions (cogs)."""
        logger.info("Starting to load extensions...")

        if self.cog_modules:
            for module in self.cog_modules:
                try:
                    logger.info(f"Loading cog: {module}")
                    await self.load_extension(module)
                    logger.info(f"[success] Successfully loaded {module}")
                except Exception as e:
                    logger.error(f"[failed] Failed to load {module}: {e}")
        else:
            logger.warning("No cogs to load")

    async def setup_hook(self):
        """Setup hook called when the bot is ready to start."""
        logger.info("Setup hook started...")

        await self.load_extensions()

        try:
            logger.info("Starting command sync...")
            synced = await self.tree.sync()
            logger.info(
                f"[success] Successfully synced {len(synced)} commands"
            )

        except Exception as e:
            logger.error(f"[failed] Sync failed: {e}")
            import traceback

            logger.error(traceback.format_exc())

        await self.init_views()

        log_tree_summary(self.tree, logger=logger)

    async def on_ready(self):
        """Event called when the bot is ready."""
        logger.info("🚀 Nightcore bot started successfully!")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info(f"Chunked guilds: {self.chunked_guilds}")
        logger.info(f"Loaded cogs: {list(self.cogs.keys())}")

        await self._warmup_discord()
