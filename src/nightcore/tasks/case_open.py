"""Finalize expired pending case opening sessions."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore

from src.infra.db.operations import (
    delete_case_open_sessions,
    get_case_open_rewards_for_update,
    get_expired_case_open_sessions_for_update,
    get_user_for_update,
)
from src.nightcore.features.economy.utils.case import give_reward_by_type

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


class CaseOpenTask(Cog):
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot
        self.finalize_expired_case_sessions.start()

    async def cog_unload(self) -> None:
        """Cancel the task when the cog unloads."""
        if self.finalize_expired_case_sessions.is_running():
            self.finalize_expired_case_sessions.cancel()

    @tasks.loop(minutes=5)
    async def finalize_expired_case_sessions(self) -> None:
        """Finalize pending case sessions that passed their deadline."""
        await self.bot.task_manager.sleep(__name__)

        try:
            async with self.bot.uow.start() as session:
                sessions = await get_expired_case_open_sessions_for_update(
                    session,
                    now=datetime.now(UTC),
                )

                for case_session in sessions:
                    user = await get_user_for_update(
                        session,
                        guild_id=case_session.guild_id,
                        user_id=case_session.user_id,
                        for_update=True,
                    )
                    rewards = await get_case_open_rewards_for_update(
                        session,
                        session_id=case_session.id,
                    )

                    if user is not None:
                        await give_reward_by_type(
                            session,
                            rewards=[reward.reward for reward in rewards],
                            user=user,
                        )

                await delete_case_open_sessions(
                    session,
                    session_ids=[case_session.id for case_session in sessions],
                )

        except Exception:
            logger.exception(
                "[task] - Failed to finalize expired case opening sessions"
            )

    @finalize_expired_case_sessions.before_loop
    async def before_finalize_expired_case_sessions(self) -> None:
        """Wait until the bot is ready before starting the task."""
        await self.bot.wait_until_ready()


async def setup(bot: "Nightcore") -> None:
    """Setup the expired case opening task."""
    await bot.add_cog(CaseOpenTask(bot))
