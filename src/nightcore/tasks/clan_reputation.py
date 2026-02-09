"""Task cog for unpunishing users."""

import asyncio
import logging

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.models import GuildClansConfig
from src.infra.db.operations import (
    get_clans_by_spec,
    get_specified_guild_config,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.clans.components.v2 import ClansPaydayViewV2
from src.nightcore.utils import ensure_messageable_channel_exists

logger = logging.getLogger(__name__)


# CRITICAL
class ClansPayDayTask(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

        self.add_clan_reputation_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.add_clan_reputation_task.is_running():
            self.add_clan_reputation_task.cancel()

    @tasks.loop(hours=1)
    async def add_clan_reputation_task(self):
        """Task to add reputation points to clans."""
        try:
            logger.info("[task] - Running add clan reputation task")

            view = ClansPaydayViewV2(bot=self.bot)

            async with self.bot.uow.start() as session:
                guilds = self.bot.guilds

                for guild in guilds:
                    clans = await get_clans_by_spec(session, guild_id=guild.id)

                    guild_config = await get_specified_guild_config(
                        session,
                        guild_id=guild.id,
                        config_type=GuildClansConfig,
                    )

                    for clan in clans:
                        # add reputation
                        added = clan.payday_multipler * len(clan.members)
                        clan.coins += added

                        logger.info(
                            "[task] - Added %s reputation to clan %s in guild %s",  # noqa: E501
                            added,
                            clan.name,
                            guild.id,
                        )

                    if (
                        not guild_config
                        or not guild_config.clan_payday_channel_id
                    ):
                        logger.warning(
                            "[task] - Guild %s does not have clan payday channel configured.",  # noqa: E501
                            guild.id,
                        )
                        continue

                    channel = await ensure_messageable_channel_exists(
                        guild, guild_config.clan_payday_channel_id
                    )
                    if not channel:
                        logger.error(
                            "[task] - Clan payday channel %s not found in guild %s",  # noqa: E501
                            guild_config.clan_payday_channel_id,
                            guild.id,
                        )
                        continue

                    try:
                        asyncio.create_task(channel.send(view=view))  # type: ignore
                    except Exception as e:
                        logger.error(
                            "[task] - Error sending clan payday message to channel %s in guild %s: %s",  # noqa: E501
                            channel.id,
                            guild.id,
                            e,
                        )
                        continue
        except Exception as e:
            logger.exception(
                "[task] - Error in add clan reputation task iteration: %s",
                e,
                exc_info=True,
            )

    @add_clan_reputation_task.before_loop
    async def before_add_clan_reputation_task(self):
        """Prepare before starting the add clan reputation task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @add_clan_reputation_task.error
    async def add_clan_reputation_task_error(self, exc: BaseException) -> None:
        """Handle errors in the add clan reputation task."""
        logger.exception(
            "[task] - Add clan reputation task crashed:",
            exc_info=exc,
        )

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.add_clan_reputation_task.is_running():
            logger.info("[task] - Restarting add clan reputation task...")
            self.add_clan_reputation_task.restart()


async def setup(bot: Nightcore):
    """Setup the ClansPayDayTask cog."""
    await bot.add_cog(ClansPayDayTask(bot))
