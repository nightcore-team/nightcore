"""Commands and finalizer for the casino roulette game."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, Message, TextChannel, app_commands
from discord.http import MultipartParameters
from discord.interactions import Interaction

from src.infra.db.models import (
    CasinoBet,
    CasinoGame,
    GuildEconomyConfig,
    GuildLoggingConfig,
)
from src.infra.db.operations import (
    get_or_create_user,
    get_specified_channel,
    get_specified_field,
)
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.economy._groups import casino as casino_group
from src.nightcore.features.economy.components.v2 import (
    MultiplayerRouletteViewV2,
    SingleRouletteViewV2,
)
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.features.economy.utils.casino import (
    register_finalizer,
)
from src.nightcore.features.economy.utils.casino.roulette import (
    RouletteColor,
    RouletteResult,
    spin_roulette,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils import ensure_messageable_channel_exists
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.utils._enums import (
    CasinoBetResultTypeEnum,
    CasinoGameStateEnum,
    CasinoGameTypeEnum,
    CasinoPlayersTypeEnum,
    ChannelType,
)

if TYPE_CHECKING:
    from src.infra.db.models._annot import CasinoBetAnnot
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


async def _send_multiplayer_roulette_message(
    bot: "Nightcore",
    channel: TextChannel,
    casino_game: CasinoGame,
    view: MultiplayerRouletteViewV2,
) -> Message:
    """Send multiplayer roulette message and persist message/channel ids."""
    message = await channel.send(view=view)
    async with bot.uow.start() as session:
        casino_game = await session.merge(casino_game)  # type: ignore
        casino_game.message_id = message.id
        casino_game.channel_id = message.channel.id

    return message


@casino_group.command(name="roulette", description="Сыграть в рулетку")  # type: ignore
@app_commands.describe(
    type="Тип игры (одиночная или мультиплеерная)",
    bet="Ваша ставка (минимум 5 коинов)",
    color="Выберите цвет",
)
@app_commands.choices(
    color=[
        app_commands.Choice(name="🔴 Красное (x2)", value="red"),
        app_commands.Choice(name="⚫ Чёрное (x2)", value="black"),
        app_commands.Choice(name="🟢 Зелёное (x14)", value="green"),
    ]
)
@app_commands.choices(
    type=[
        app_commands.Choice(name="Одиночная игра", value="single"),
        app_commands.Choice(
            name="Многопользовательская игра", value="multiplayer"
        ),
    ]
)
@app_commands.checks.cooldown(1, 15.0, key=lambda i: i.user.id)
@check_required_permissions(PermissionsFlagEnum.NONE)
async def roulette(
    interaction: Interaction["Nightcore"],
    type: app_commands.Choice[str],
    bet: app_commands.Range[int, 5, 1000000],
    color: str,
):
    """Play roulette game."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    selected_color: RouletteColor = cast(RouletteColor, color)

    outcome = ""
    result: RouletteResult | None = None
    logging_channel_id: int | None = None
    new_balance = 0
    casino_game: CasinoGame | None = None
    casino_game_id: int | None = None
    casino_multiplayer_channel_id: int | None = None

    async with specified_guild_config(
        bot, guild_id=guild.id, config_type=GuildEconomyConfig
    ) as (guild_config, session):
        try:
            user_record, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=member.id,
            )
            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )
            casino_multiplayer_channel_id = (
                guild_config.casino_multiplayer_channel_id
            )

            if user_record.coins < bet:
                outcome = "insufficient_balance"
            else:
                casino_game = CasinoGame(
                    guild_id=guild.id,
                    initiator_id=member.id,
                    game_type=CasinoGameTypeEnum.ROULETTE,
                    end_time=datetime.now(UTC),
                )
                casino_bet = CasinoBet(
                    user_id=user_record.id,
                    option=selected_color,
                )

                if type.value == "single":
                    number, spin_color = spin_roulette()
                    result = RouletteResult(
                        number, spin_color, bet, selected_color
                    )
                    casino_game.players_type = CasinoPlayersTypeEnum.SINGLE
                    casino_game.state = CasinoGameStateEnum.FINISHED
                    casino_bet.amount = bet

                    # Update user balance
                    user_record.coins += result.coins_change
                    new_balance = user_record.coins

                    logger.info(
                        "[roulette] User %s bet %d on %s, got %d (%s), "
                        "%s %d coins in guild %s",
                        member.id,
                        bet,
                        selected_color,
                        number,
                        spin_color,
                        "won" if result.is_win else "lost",
                        abs(result.coins_change),
                        guild.id,
                    )
                else:
                    casino_game.players_type = (
                        CasinoPlayersTypeEnum.MULTIPLAYER
                    )
                    casino_game.state = CasinoGameStateEnum.PENDING
                    casino_game.end_time = casino_game.end_time + timedelta(
                        minutes=1
                    )
                    user_record.coins -= bet
                    casino_bet.amount = bet * 2

                session.add(casino_game)
                await session.flush()
                casino_game_id = casino_game.id
                casino_bet.game_id = casino_game_id

                session.add(casino_bet)

                outcome = "success"

        except Exception as e:
            logger.exception(
                "[roulette] Error in roulette for user %s in guild %s: %s",
                member.id,
                guild.id,
                e,
            )
            outcome = "error"

    if outcome == "insufficient_balance":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка ставки",
                "У вас недостаточно коинов для ставки.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка игры",
                "Произошла ошибка при игре в рулетку.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        coin_name = guild_config.coin_name or "коины"
        reward_coin_name = guild_config.coin_name or "коинов"

        if type.value == "single":
            if result is None:
                logger.error(
                    "[roulette] Result is None for single game, "
                    "user %s in guild %s",
                    member.id,
                    guild.id,
                )
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка игры",
                        "Произошла ошибка при игре в рулетку.",
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            view = SingleRouletteViewV2(
                bot=bot,
                coin_name=reward_coin_name,
                result=result,
                new_balance=new_balance,
            )

            # Dispatch award notification event for single player
            bot.dispatch(
                "user_items_changed",
                dto=AwardNotificationEventDTO(
                    guild=guild,
                    event_type="casino/roulette",
                    logging_channel_id=logging_channel_id,
                    user_id=member.id,
                    moderator_id=bot.user.id,  # type: ignore
                    item_name=coin_name,
                    amount=result.coins_change,
                    reason="игра в рулетку",
                ),
            )

            return await interaction.response.send_message(
                view=view, ephemeral=True
            )
        else:
            assert casino_game is not None

            view = MultiplayerRouletteViewV2(
                bot=bot,
                coin_name=coin_name,
                initiator_id=member.id,
                initiator_bet=bet,
                state=CasinoGameStateEnum.PENDING,
                initiator_selected_color=selected_color,
            )

            channel: TextChannel
            success_detail: str
            error_detail: str
            ephemeral: bool

            if casino_multiplayer_channel_id is None:
                channel = cast(TextChannel, interaction.channel)
                success_detail = "Ваша игра отправлена в канал {jump}."
                error_detail = (
                    "Не удалось отправить сообщение в текущий канал."
                )
                ephemeral = True
            else:
                target_channel = await ensure_messageable_channel_exists(
                    guild, casino_multiplayer_channel_id
                )
                if target_channel is None:
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка канала",
                            (
                                "Канал многопользовательской рулетки "
                                "не найден или недоступен."
                            ),
                            bot.user.display_name,  # type: ignore
                            bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                channel = cast(TextChannel, target_channel)
                success_detail = (
                    "Ваша игра отправлена в канал {jump}.\nОстальные игроки "
                    "могут присоединиться к игре в течение 1 минуты нажав "
                    "на ссылку"
                )
                error_detail = (
                    "Не удалось отправить сообщение в канал "
                    "многопользовательской рулетки."
                )
                ephemeral = False

            try:
                message = await _send_multiplayer_roulette_message(
                    bot=bot,
                    channel=channel,
                    casino_game=casino_game,
                    view=view,
                )
            except Exception as e:
                logger.exception(
                    "[roulette] Failed to send multiplayer "
                    "roulette message in guild %s: %s",
                    guild.id,
                    e,
                )
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка отправки",
                        error_detail,
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            return await interaction.response.send_message(
                embed=SuccessMoveEmbed(
                    "Игра отправлена",
                    success_detail.format(jump=message.jump_url),
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=ephemeral,
            )


@register_finalizer(CasinoGameTypeEnum.ROULETTE)
async def finish_roulette(bot: "Nightcore", game: CasinoGame) -> None:
    """Finish a single multiplayer roulette game and post results."""
    try:
        async with bot.uow.start() as session:
            game = await session.merge(game, load=False)  # type: ignore

            coin_name = await get_specified_field(
                session,
                guild_id=game.guild_id,
                config_type=GuildEconomyConfig,
                field_name="coin_name",
            )

            bets_annot: list[CasinoBetAnnot] = []
            initiator_id = 0
            initiator_bet = 0
            initiator_selected_color = ""
            initiator_result_coins: int | None = None

            num, color = spin_roulette()

            # Process all bets and update user balances
            for bet in game.bets:
                result = RouletteResult(
                    num, color, bet.amount // 2, bet.option
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
                    initiator_selected_color = bet.option
                    initiator_result_coins = result.coins_change
                else:
                    bets_annot.append(
                        {
                            "user_id": bet.user.user_id,
                            "bet": bet.amount // 2,
                            "result_coins": result.coins_change,
                            "selected_color": bet.option,
                        }
                    )

            game.state = CasinoGameStateEnum.FINISHED

            message_id = game.message_id
            channel_id = game.channel_id

        # Send Discord message outside transaction
        await asyncio.sleep(0.2)  # to avoid rate limits

        view = MultiplayerRouletteViewV2(
            bot=bot,
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
            bot.http.edit_message(
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
            "[roulette] - Ended multiplayer roulette game %s in guild %s",
            game.id,
            game.guild_id,
        )

    except Exception as e:
        logger.exception(
            "[roulette] - Error processing roulette game %s in guild %s: %s",
            game.id,
            game.guild_id,
            e,
            exc_info=True,
        )
