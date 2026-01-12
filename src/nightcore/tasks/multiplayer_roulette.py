"""Task cog for ending multiplayer roulette game."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from discord.ext import tasks
from discord.ext.commands import Cog  # type: ignore
from discord.http import MultipartParameters

from src.infra.db.models._enums import (
    CasinoBetResultTypeEnum,
    CasinoGameStateEnum,
)
from src.infra.db.models.guild import GuildEconomyConfig
from src.infra.db.operations import (
    get_active_casino_games,
    get_specified_field,
)
from src.nightcore.bot import Nightcore
from src.nightcore.features.economy.components.v2 import (
    MultiplayerRouletteViewV2,
)
from src.nightcore.features.economy.utils.casino import (
    RouletteResult,
    spin_roulette,
)

if TYPE_CHECKING:
    from src.infra.db.models._annot import CasinoBetAnnot


logger = logging.getLogger(__name__)


class MultiplayerRouletteTask(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

        self.end_multiplayer_roulette_game_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.end_multiplayer_roulette_game_task.is_running():
            self.end_multiplayer_roulette_game_task.cancel()

    @tasks.loop(seconds=15)
    async def end_multiplayer_roulette_game_task(self):
        """Task to add reputation points to clans."""
        logger.info("[task] - Running add clan reputation task")

        # get all multiplayer roulette games that need to be ended (state and end_time)  # noqa: E501
        async with self.bot.uow.start() as session:
            guilds = self.bot.guilds
            for guild in guilds:
                casino_games = await get_active_casino_games(
                    session, guild_id=guild.id, dt=datetime.now(UTC)
                )
                coin_name = await get_specified_field(
                    session,
                    guild_id=guild.id,
                    config_type=GuildEconomyConfig,
                    field_name="coin_name",
                )
                if casino_games:
                    for game in casino_games:
                        bets_annot: list[CasinoBetAnnot] = []
                        initiator_id = 0
                        initiator_bet = 0
                        initiator_selected_color = ""
                        initiator_result: CasinoBetResultTypeEnum | None = None
                        num, color = spin_roulette()
                        for bet in game.bets:
                            if bet.user_id == game.initiator_id:
                                initiator_id = bet.user_id
                                initiator_bet = bet.amount
                                initiator_selected_color = bet.color
                                initiator_result = bet.result_type

                            result = RouletteResult(
                                num, color, bet.amount, bet.color
                            )
                            result_type: CasinoBetResultTypeEnum

                            if result.is_win:
                                result_type = CasinoBetResultTypeEnum.WIN
                            else:
                                result_type = CasinoBetResultTypeEnum.LOSE
                            bet.result_type = result_type
                            bet.user.coins += result.coins_change

                            bets_annot.append(
                                {
                                    "user_id": bet.user_id,
                                    "bet": bet.amount,
                                    "result_type": result_type,
                                    "selected_color": bet.color,
                                }
                            )

                        game.state = CasinoGameStateEnum.FINISHED

                        await asyncio.sleep(0.2)  # to avoid rate limits

                        view = MultiplayerRouletteViewV2(
                            bot=self.bot,
                            coin_name=coin_name or "коинов",
                            initiator_id=initiator_id,
                            initiator_bet=initiator_bet,
                            initiator_selected_color=initiator_selected_color,
                            initiator_result=initiator_result,
                            state=CasinoGameStateEnum.FINISHED,
                            bets=bets_annot,
                        )

                        asyncio.create_task(
                            self.bot.http.edit_message(
                                message_id=game.message_id,
                                channel_id=game.channel_id,
                                params=MultipartParameters(
                                    payload={
                                        "components": view.to_components(),
                                    },
                                    multipart=None,
                                    files=None,
                                ),
                            )
                        )

                        logger.info(
                            "[task] - Ended multiplayer roulette game %s in guild %s",  # noqa: E501
                            game.id,
                            guild.id,
                        )
                else:
                    logger.info(
                        "[task] - No multiplayer roulette games to end in guild %s",  # noqa: E501
                        guild.id,
                    )
                    continue

    @end_multiplayer_roulette_game_task.before_loop
    async def before_end_multiplayer_roulette_game_task(self):
        """Prepare before starting the end multiplayer roulette game task."""
        logger.info("[task] - Waiting for bot...")
        await self.bot.wait_until_ready()

    @end_multiplayer_roulette_game_task.error
    async def end_multiplayer_roulette_game_task_error(
        self, exc: BaseException
    ) -> None:
        """Handle errors in the end multiplayer roulette game task."""
        logger.exception(
            "[task] - End multiplayer roulette game task crashed:",
            exc_info=exc,
        )
        raise exc


async def setup(bot: Nightcore):
    """Setup the MultiplayerRouletteTask cog."""
    await bot.add_cog(MultiplayerRouletteTask(bot))
