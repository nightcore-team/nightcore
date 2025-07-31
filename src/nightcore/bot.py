"""Nightcore Bot."""

import logging

import discord
from discord.ext.commands import (
    Bot,
    Cog,
)

logger = logging.getLogger(__name__)


class Nightcore(Bot):
    def __init__(self, *, initial_cogs: list[Cog] | None = None):
        self.initial_cogs = initial_cogs
        super().__init__(
            command_prefix=".",
            intents=discord.Intents.all(),
            help_command=None,
        )

    async def load_extensions(self) -> None:
        """Load all bot extensions (cogs)."""
        logger.info("Starting to load extensions...")

        if self.initial_cogs:
            for cog in self.initial_cogs:
                try:
                    logger.info(f"Loading cog: {cog.__cog_name__}")
                    await self.add_cog(cog(self))  # type: ignore
                    logger.info(
                        f"[success] Successfully loaded {cog.__cog_name__}"
                    )
                except Exception as e:
                    logger.error(
                        f"[failed] Failed to load {cog.__cog_name__}: {e}"
                    )
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

    async def on_ready(self):
        """Event called when the bot is ready."""
        logger.info("🚀 Nightcore bot started successfully!")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info(f"Loaded cogs: {list(self.cogs.keys())}")
