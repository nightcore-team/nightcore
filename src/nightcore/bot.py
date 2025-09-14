"""Nightcore Bot."""

import contextlib
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext.commands import Bot  # type: ignore

from src.infra.db.uow import UnitOfWork
from src.nightcore.utils import log_tree_summary

logger = logging.getLogger(__name__)


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
        super().__init__(
            command_prefix=".",
            intents=discord.Intents.all(),
            help_command=None,
            tree_cls=GuildOnlyTree,
        )
        self.chunked_guilds: int = 0
        self.startup_time: datetime = datetime.now(timezone.utc)

    async def chunk_guilds(self) -> None:
        """Ensure all guilds are chunked."""
        for guild in self.guilds:
            if not guild.chunked:
                logger.info(f"Chunking guild: {guild.name} ({guild.id})")
                await guild.chunk(cache=True)
                logger.info(f"[success] Chunked guild: {guild.name}")
                self.chunked_guilds += 1

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

        await self.chunk_guilds()

        log_tree_summary(self.tree, logger=logger)

    async def on_ready(self):
        """Event called when the bot is ready."""
        logger.info("🚀 Nightcore bot started successfully!")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info(f"Chunked guilds: {self.chunked_guilds}")
        logger.info(f"Loaded cogs: {list(self.cogs.keys())}")
