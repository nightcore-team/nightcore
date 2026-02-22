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

if TYPE_CHECKING:
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
    def __init__(self, bot: "Nightcore") -> None:
        self.bot = bot

        self.end_multiplayer_roulette_game_task.start()

    async def cog_unload(self):
        """Unload the cog and cancel the task if running."""
        if self.end_multiplayer_roulette_game_task.is_running():
            self.end_multiplayer_roulette_game_task.cancel()

    async def _process_single_game(
        self, game_id: int, guild_id: int, coin_name: str | None
    ):
        """Process a single casino game in its own transaction."""
        try:
            # Use a separate session for each game to avoid long transactions
            async with self.bot.uow.start() as session:
                # Re-fetch the game with all relations in this session
                casino_games = await get_active_casino_games(
                    session, guild_id=guild_id, dt=datetime.now(UTC)
                )

                # Find the specific game we want to process
                game = next((g for g in casino_games if g.id == game_id), None)
                if not game:
                    logger.warning(
                        "[task] - Game %s not found or already processed",
                        game_id,
                    )
                    return

                bets_annot: list[CasinoBetAnnot] = []
                initiator_id = 0
                initiator_bet = 0
                initiator_selected_color = ""
                initiator_result_coins: int | None = None

                num, color = spin_roulette()

                # Process all bets and update user balances
                for bet in game.bets:
                    result = RouletteResult(
                        num, color, bet.amount // 2, bet.color
                    )
                    result_type: CasinoBetResultTypeEnum

                    if result.is_win:
                        result_type = CasinoBetResultTypeEnum.WIN
                        bet.user.coins += result.coins_change * 2
                    else:
                        result_type = CasinoBetResultTypeEnum.LOSE

                    bet.result_type = result_type

                    if bet.user.user_id == game.initiator_id:
                        initiator_id = bet.user.user_id
                        initiator_bet = bet.amount // 2
                        initiator_selected_color = bet.color
                        initiator_result_coins = result.coins_change
                    else:
                        bets_annot.append(
                            {
                                "user_id": bet.user.user_id,
                                "bet": bet.amount // 2,
                                "result_coins": result.coins_change,
                                "selected_color": bet.color,
                            }
                        )

                game.state = CasinoGameStateEnum.FINISHED

                # Session commits here when context exits
                message_id = game.message_id
                channel_id = game.channel_id

            # Send Discord message outside transaction
            await asyncio.sleep(0.2)  # to avoid rate limits

            view = MultiplayerRouletteViewV2(
                bot=self.bot,
                coin_name=coin_name or "коинов",
                initiator_id=initiator_id,
                initiator_bet=initiator_bet,
                initiator_selected_color=initiator_selected_color,
                initiator_result_coins=initiator_result_coins,
                state=CasinoGameStateEnum.FINISHED,
                result_color=color,
                bets=bets_annot,
                disable_buttons=True,
            )

            asyncio.create_task(
                self.bot.http.edit_message(
                    message_id=message_id,
                    channel_id=channel_id,
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
                "[task] - Ended multiplayer roulette game %s in guild %s",
                game_id,
                guild_id,
            )

        except Exception as e:
            logger.exception(
                "[task] - Error processing game %s in guild %s: %s",
                game_id,
                guild_id,
                e,
                exc_info=True,
            )

    @tasks.loop(seconds=15)
    async def end_multiplayer_roulette_game_task(self):
        """Task to add reputation points to clans."""
        try:
            logger.info("[task] - Running end multiplayer roulette task")

            guilds = self.bot.guilds

            for guild in guilds:
                # Separate session for reading games list
                async with self.bot.uow.start() as session:
                    casino_games = await get_active_casino_games(
                        session, guild_id=guild.id, dt=datetime.now(UTC)
                    )
                    coin_name = await get_specified_field(
                        session,
                        guild_id=guild.id,
                        config_type=GuildEconomyConfig,
                        field_name="coin_name",
                    )

                    # Extract game IDs to process
                    game_ids = [game.id for game in casino_games]

                if not game_ids:
                    logger.info(
                        "[task] - No multiplayer roulette games to end in "
                        "guild %s",
                        guild.id,
                    )
                    continue

                # Process each game in its own transaction
                for game_id in game_ids:
                    await self._process_single_game(
                        game_id, guild.id, coin_name
                    )

        except Exception as e:
            logger.exception(
                "[task] - Error in end multiplayer roulette game task "
                "iteration: %s",
                e,
                exc_info=True,
            )

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

        # Wait before restarting to avoid rapid restart loops
        await asyncio.sleep(60)

        if not self.end_multiplayer_roulette_game_task.is_running():
            logger.info(
                "[task] - Restarting end multiplayer roulette game task..."
            )
            self.end_multiplayer_roulette_game_task.restart()


async def setup(bot: "Nightcore"):
    """Setup the MultiplayerRouletteTask cog."""
    await bot.add_cog(MultiplayerRouletteTask(bot))
