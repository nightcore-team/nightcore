"""Nightcore Bot."""

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any

import discord
import discordhealthcheck  # type: ignore
from aiohttp import TCPConnector
from discord import ClientUser, app_commands
from discord.ext.commands import Bot  # type: ignore
from nightforo import Client as XenforoClient

from src.config.config import config
from src.infra.db.operations import reset_users_voice_activity
from src.infra.db.uow import UnitOfWork
from src.nightcore.exceptions import CommandDontHavePermissionsFlagError
from src.nightcore.features.clans.components.v2 import ClanShopViewV2
from src.nightcore.features.economy.components.v2 import (
    CoinsShopOrderViewV2,
    CoinsShopViewV2,
)
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
from src.nightcore.utils.image_builder.cache import ImageCache

logger = logging.getLogger(__name__)


class CustomAPICollection:
    def __init__(self):
        pass

    @property
    def forum(self) -> XenforoClient:
        """Get the Forum API client."""
        return XenforoClient(api_key=config.forum.FORUM_API_KEY)


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
    user: ClientUser  # type: ignore

    def __init__(
        self,
        *,
        cog_modules: list[str],
        uow: UnitOfWork,
    ):
        self.cog_modules = cog_modules
        self.uow = uow
        self.apis = CustomAPICollection()
        self.images_cache = ImageCache()
        self.config = config

        super().__init__(
            command_prefix=".",
            intents=discord.Intents.all(),
            help_command=None,
            tree_cls=GuildOnlyTree,
            chunk_guilds_at_startup=True,
        )
        self.chunked_guilds: int = 0
        self.startup_time: datetime = datetime.now(UTC)

    async def startup(self):
        """Run the bot with graceful shutdown via async context manager."""

        async with self:
            await self.start(config.bot.BOT_TOKEN)

    @property
    def _http_connector(self) -> TCPConnector:
        return TCPConnector(
            limit=100,  # max 100 connections
            ttl_dns_cache=60,  # Refresh DNS more often on unstable hosts
            enable_cleanup_closed=True,
            force_close=False,  # Don't close connection after each request  # noqa: E501
            keepalive_timeout=60,  # Keep connection alive for 60 seconds
        )

    async def _reset_users_voice_activity(self) -> None:
        """Reset users' voice activity status in the database on startup."""
        try:
            async with self.uow.start() as session:
                count = await reset_users_voice_activity(session)
            logger.info(
                "[reset/voice] Successfully reset %d users' voice activity status.",  # noqa: E501
                count,
            )
        except Exception as e:
            logger.error(
                "[reset/voice] Failed to reset users' voice activity status: %s",  # noqa: E501
                e,
            )

    def init_views(self) -> None:
        """Initialize persistent views."""

        views: list[discord.ui.LayoutView] = [
            CreateTicketViewV2(self),
            ClanShopViewV2(self, _build=True),
            CoinsShopViewV2(self),
            CoinsShopOrderViewV2(self, _build=True),
            ManageTicketViewV2(self),
            CheckRoleRequestView(self),
            SendRoleRequestView(self),
            NotifyViewV2(self, _build=True),
            ProposalViewV2(self, _build=True),
        ]

        for view in views:
            logger.info(
                "[views] Loading persistent view: %s", view.__class__.__name__
            )
            self.add_view(view)

    def _validate_commands_permissions(
        self,
        commands: list[
            app_commands.Command[Any, ..., Any]
            | app_commands.Group
            | app_commands.ContextMenu
        ],
    ) -> None:
        """Validate that all commands have __permissions_flag__ attribute.

        Args:
            commands: List of commands to validate

        Raises:
            CommandDontHavePermissionsFlagError: If command doesn't have permission flag
        """  # noqa: E501

        def _check_command(
            cmd: app_commands.Command[Any, ..., Any], path: str = ""
        ) -> None:
            """Recursively check command for permission flag."""

            if not hasattr(cmd.callback, "__permissions_flag__"):
                raise CommandDontHavePermissionsFlagError(
                    f"Command '{path}' is missing __permissions_flag__ attribute"  # noqa: E501
                )
            else:
                logger.info(
                    "[permissions] Command %s has __permissions_flag__: %s",
                    path,
                    cmd.callback.__permissions_flag__,  # type: ignore
                )

        def _check_group(group: app_commands.Group, path: str = "") -> None:
            """Recursively check group and its subcommands."""
            current_path = f"{path} {group.name}".strip()

            for sub_cmd in group.commands:
                if isinstance(sub_cmd, app_commands.Group):
                    _check_group(sub_cmd, current_path)
                else:
                    _check_command(sub_cmd, f"{current_path} {sub_cmd.name}")

        for cmd in commands:
            if isinstance(cmd, app_commands.Group):
                _check_group(cmd)
            elif isinstance(cmd, app_commands.Command):
                _check_command(cmd, cmd.name)
            else:
                logger.warning(
                    "[permissions] Ignore app_commands.ContextMenu in permission validation: %s",  # noqa: E501
                    cmd.name,
                )

            logger.info(
                "[permissions] Validating permissions flag for command: %s",
                cmd.name,
            )

    async def load_extensions(self) -> None:
        """Load all bot extensions (cogs)."""
        logger.info("[extensions] Starting to load extensions...")

        if self.cog_modules:
            for module in self.cog_modules:
                try:
                    if (
                        "check_forum" in module
                        and config.bot.DISABLE_FORUM_TASK
                    ):
                        logger.info(
                            "[extensions] Skipping loading cog %s because forum task is disabled.",  # noqa: E501
                            module,
                        )
                        continue

                    logger.info("[extensions] Loading cog: %s", module)
                    await self.load_extension(module)
                    logger.info("[success] Successfully loaded %s", module)
                except Exception as e:
                    logger.error("[failed] Failed to load %s: %s", module, e)
        else:
            logger.warning("[extensions] No cogs to load")

    async def setup_hook(self):
        """Setup hook called when the bot is ready to start."""
        logger.info("[setup] Setup hook started...")

        logger.info("[healthcheck] Running discord health check...")
        self.healthcheck_server = await discordhealthcheck.start(self)

        await self.load_extensions()

        self.http.connector = self._http_connector

        commands = self.tree.get_commands()

        self._validate_commands_permissions(commands)

        try:
            logger.info("[sync] Starting command sync...")
            synced = await self.tree.sync()
            logger.info(
                "[success] Successfully synced %d commands",
                len(synced),
            )

        except Exception as e:
            logger.error("[failed] Sync failed: %s", e)
            import traceback

            logger.error(traceback.format_exc())

        self.init_views()

        await self._reset_users_voice_activity()

        log_tree_summary(self.tree, logger=logger)

    async def on_ready(self):
        """Event called when the bot is ready."""
        logger.info(f"Loaded cogs: {list(self.cogs.keys())}")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info(f"Chunked guilds: {self.chunked_guilds}")
        logger.info("🚀 Nightcore bot started successfully!")
