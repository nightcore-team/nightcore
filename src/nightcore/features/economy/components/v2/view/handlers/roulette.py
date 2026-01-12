"""Handle roulette multiplayer join button callback."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from discord import Guild, Message
from discord.interactions import Interaction

from src.infra.db.models._enums import CasinoGameStateEnum
from src.infra.db.operations import get_casino_game_by_message_id
from src.nightcore.components.embed import ErrorEmbed

if TYPE_CHECKING:
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
    async with bot.uow.start() as session:
        casino_game = await get_casino_game_by_message_id(
            session, guild_id=guild.id, message_id=message.id, with_bets=True
        )

        if not casino_game:
            outcome = "game_not_found"
        else:
            if casino_game.state == CasinoGameStateEnum.FINISHED:
                outcome = "game_finished"
            else:
                for bet in casino_game.bets:
                    if bet.user_id == interaction.user.id:
                        await session.delete(bet)
                        outcome = "leave_success"
                        break
                else:
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

    if outcome == "leave_success":
        return await interaction.response.send_message(
            "Вы успешно покинули игру в рулетку.",
            ephemeral=True,
        )

    if outcome == "join_success":
        await interaction.response.send_modal(
            JoinMultiplayerRouletteModal(bot=bot, message=message)
        )
