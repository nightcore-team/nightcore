"""Modal for join to multiplayer roulette game."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from discord import Guild, Message, SelectOption, TextStyle
from discord.interactions import Interaction
from discord.ui import Label, Modal, Select, TextInput

from src.infra.db.models import CasinoBet, GuildEconomyConfig
from src.infra.db.models._enums import CasinoGameStateEnum
from src.infra.db.operations import (
    get_casino_game_by_message_id,
    get_or_create_user,
    get_specified_field,
)

if TYPE_CHECKING:
    from src.infra.db.models._annot import CasinoBetAnnot
    from src.nightcore.bot import Nightcore


from src.nightcore.components.embed import ErrorEmbed, ValidationErrorEmbed
from src.nightcore.features.economy.components.v2 import (
    MultiplayerRouletteViewV2,
)

logger = logging.getLogger(__name__)


class JoinMultiplayerRouletteModal(
    Modal, title="Присоединиться к игре в рулетку"
):
    color = Label["JoinMultiplayerRouletteModal"](
        text="Выберите цвет",
        component=Select(
            placeholder="Выберите цвет вашей ставки",
            options=[
                SelectOption(
                    label="🔴 Красное (x2)",
                    value="red",
                ),
                SelectOption(
                    label="⚫ Чёрное (x2)",
                    value="black",
                ),
                SelectOption(
                    label="🟢 Зелёное (x14)",
                    value="green",
                ),
            ],
            required=True,
        ),
    )
    short = TextInput["JoinMultiplayerRouletteModal"](
        label="Введите ставку",
        style=TextStyle.short,
        placeholder="Минимальная: 5 коинов",
        required=True,
        min_length=1,
    )

    def __init__(
        self,
        bot: Nightcore,
        message: Message,
    ):
        super().__init__()
        self.bot = bot
        self.message = message

    async def on_submit(self, interaction: Interaction) -> None:
        """Handles the submission of the join multiplayer roulette modal."""

        # create bet for specified game and user
        selected_color: str = self.color.component.values[0]  # type: ignore

        try:
            amount = int(self.short.value)
        except ValueError:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Ошибка присоединения",
                    "Пожалуйста, введите корректное числовое значение для ставки.",  # noqa: E501
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if amount < 5:
            return await interaction.response.send_message(
                embed=ValidationErrorEmbed(
                    "Ошибка присоединения",
                    "Ставка должна быть не менее 5 коинов.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        bot = self.bot
        guild = cast(Guild, interaction.guild)
        outcome = ""

        initiator_id = 0
        initiator_bet = 0
        initiator_selected_color = ""
        bets: list[CasinoBetAnnot] = []

        async with bot.uow.start() as session:
            user_record, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=interaction.user.id
            )
            coin_name: str | None = await get_specified_field(
                session,
                guild_id=guild.id,
                config_type=GuildEconomyConfig,
                field_name="coin_name",
            )

            if user_record.coins < amount:
                outcome = "insufficient_funds"
            else:
                casino_game = await get_casino_game_by_message_id(
                    session,
                    guild_id=guild.id,
                    message_id=self.message.id,
                    with_bets=True,
                )
                if not casino_game:
                    outcome = "game_not_found"
                else:
                    if casino_game.state == CasinoGameStateEnum.FINISHED:
                        outcome = "game_finished"
                    else:
                        bet = CasinoBet(
                            user_id=user_record.id,
                            amount=amount * 2,
                            color=selected_color,
                            game_id=casino_game.id,
                        )

                        casino_game.end_time = (
                            casino_game.end_time + timedelta(minutes=1)
                        )

                        session.add(bet)
                        await session.flush()

                        # Refresh relationship
                        await session.refresh(casino_game, ["bets"])

                        user_record.coins -= amount

                        outcome = "success"

                        for bet in casino_game.bets:
                            if bet.user.user_id == casino_game.initiator_id:  # type: ignore
                                initiator_id = bet.user.user_id
                                initiator_bet = bet.amount // 2
                                initiator_selected_color = bet.color
                            else:
                                bets.append(
                                    {
                                        "user_id": bet.user.user_id,
                                        "bet": bet.amount // 2,
                                        "result_coins": None,
                                        "selected_color": bet.color,
                                    }
                                )

        if outcome == "insufficient_funds":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка присоединения",
                    "У вас недостаточно коинов для этой ставки.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "game_not_found":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка присоединения",
                    "Игра не найдена. Пожалуйста, убедитесь, что игра все еще активна.",  # noqa: E501
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "game_finished":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка присоединения",
                    "Игра уже завершена. Вы не можете присоединиться к ней.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            view = MultiplayerRouletteViewV2(
                bot=bot,
                state=casino_game.state,  # type: ignore
                coin_name=coin_name,
                initiator_id=initiator_id,
                initiator_bet=initiator_bet,
                initiator_selected_color=initiator_selected_color,
                bets=bets,
            )

            try:
                await self.message.edit(view=view)
            except Exception as e:
                logger.error(
                    "Failed to update multiplayer roulette message after user joined: %s",  # noqa: E501
                    e,
                    exc_info=True,
                )

        await interaction.response.send_message(
            f"Вы успешно присоединились к игре в рулетку со ставкой {amount} коинов на цвет {selected_color}.",  # noqa: E501
            ephemeral=True,
        )
