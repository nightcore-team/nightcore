"""Handle roulette multiplayer join button callback."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from discord import Guild, Message
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.models._enums import CasinoGameStateEnum
from src.infra.db.operations import (
    get_casino_game_by_message_id,
    get_specified_field,
)
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.economy.components.v2 import (
    MultiplayerRouletteViewV2,
)

if TYPE_CHECKING:
    from src.infra.db.models._annot import CasinoBetAnnot
    from src.nightcore.bot import Nightcore

from src.nightcore.features.economy.components.modal import (
    JoinMultiplayerRouletteModal,
)


async def handle_roulette_multiplayer_join_button_callback(
    interaction: Interaction[Nightcore],
):
    """Handle roulette multiplayer join button callback."""

    # check if user is already in this game

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    message = cast(Message, interaction.message)

    outcome = ""
    initiator_id = 0
    initiator_bet = 0
    initiator_selected_color = ""
    bets: list[CasinoBetAnnot] = []

    async with bot.uow.start() as session:
        casino_game = await get_casino_game_by_message_id(
            session, guild_id=guild.id, message_id=message.id, with_bets=True
        )

        coin_name: str | None = await get_specified_field(
            session,
            guild_id=guild.id,
            config_type=GuildEconomyConfig,
            field_name="coin_name",
        )

        if not casino_game:
            outcome = "game_not_found"
        else:
            if casino_game.state == CasinoGameStateEnum.FINISHED:
                outcome = "game_finished"
            else:
                if interaction.user.id == casino_game.initiator_id:
                    outcome = "initiator_cannot_leave"
                else:
                    user_in_game = False
                    for bet in casino_game.bets:
                        if bet.user.user_id == interaction.user.id:
                            user_in_game = True
                            break

                    if user_in_game:
                        # User wants to leave
                        outcome = "leave_success"

                        # Collect bets excluding the leaving user
                        for bet in casino_game.bets:
                            if bet.user.user_id == casino_game.initiator_id:  # type: ignore
                                initiator_id = bet.user.user_id
                                initiator_bet = bet.amount // 2
                                initiator_selected_color = bet.color
                            elif bet.user.user_id != interaction.user.id:
                                bets.append(
                                    {
                                        "user_id": bet.user.user_id,
                                        "bet": bet.amount // 2,
                                        "result_coins": None,
                                        "selected_color": bet.color,
                                    }
                                )
                    else:
                        # User wants to join
                        outcome = "join_success"

    if outcome == "game_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка присоединения",
                "Игра не найдена.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "game_finished":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка присоединения",
                "Игра уже завершена.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "initiator_cannot_leave":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выхода",
                "Инициатор игры не может покинуть/присоединиться к игре.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "leave_success":
        view = MultiplayerRouletteViewV2(
            bot=bot,
            coin_name=coin_name,
            initiator_id=initiator_id,
            initiator_bet=initiator_bet,
            initiator_selected_color=initiator_selected_color,
            bets=bets,
            state=CasinoGameStateEnum.PENDING,
        )

        asyncio.create_task(message.edit(view=view))

        return await interaction.response.send_message(
            "Вы успешно покинули игру в рулетку.",
            ephemeral=True,
        )

    if outcome == "join_success":
        await interaction.response.send_modal(
            JoinMultiplayerRouletteModal(bot=bot, message=message)
        )
