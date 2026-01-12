"""Command to play casino roulette game."""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, TextChannel, app_commands
from discord.interactions import Interaction

from src.infra.db.models import (
    CasinoBet,
    CasinoGame,
    GuildEconomyConfig,
    GuildLoggingConfig,
)
from src.infra.db.models._enums import (
    CasinoGameStateEnum,
    CasinoGameTypeEnum,
    CasinoPlayersTypeEnum,
    ChannelType,
)
from src.infra.db.operations import (
    get_or_create_user,
    get_specified_channel,
)
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.economy._groups import casino as casino_group
from src.nightcore.features.economy.components.v2 import (
    MultiplayerRouletteViewV2,
    SingleRouletteViewV2,
)
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.features.economy.utils.casino import (
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

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


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

                if type.value == "single":
                    number, spin_color = spin_roulette()
                    result = RouletteResult(
                        number, spin_color, bet, selected_color
                    )
                    casino_game.players_type = CasinoPlayersTypeEnum.SINGLE
                    casino_game.state = CasinoGameStateEnum.FINISHED

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

                session.add(casino_game)
                await session.flush()
                casino_game_id = casino_game.id

                session.add(
                    CasinoBet(
                        user_id=user_record.id,
                        amount=bet,
                        color=selected_color,
                        game_id=casino_game_id,
                    )
                )

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
            view = MultiplayerRouletteViewV2(
                bot=bot,
                coin_name=coin_name,
                initiator_id=member.id,
                initiator_bet=bet,
                state=CasinoGameStateEnum.PENDING,
                initiator_selected_color=selected_color,
            )

            if casino_multiplayer_channel_id is None:
                message = await cast(TextChannel, interaction.channel).send(
                    view=view
                )
                async with bot.uow.start() as session:
                    casino_game = await session.merge(casino_game)  # type: ignore
                    casino_game.message_id = message.id
                    casino_game.channel_id = message.channel.id

                return await interaction.response.send_message(
                    embed=SuccessMoveEmbed(
                        "Игра отправлена",
                        f"Ваша игра отправлена в канал {message.jump_url}.",
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            channel = cast(
                TextChannel,
                await ensure_messageable_channel_exists(
                    guild, casino_multiplayer_channel_id
                ),
            )
            if channel:
                try:
                    message = await channel.send(
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
                            "Ошибка канала",
                            "Не удалось отправить сообщение в канал "
                            "многопользовательской рулетки.",
                            bot.user.display_name,  # type: ignore
                            bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

                async with bot.uow.start() as session:
                    casino_game = await session.merge(casino_game)  # type: ignore
                    casino_game.message_id = message.id

                return await interaction.response.send_message(
                    embed=SuccessMoveEmbed(
                        "Игра отправлена",
                        f"Ваша игра отправлена в канал {message.jump_url}.\nОстальные игроки могут присоединиться к игре в течение 1 минуты нажав на ссылку",  # noqa: E501
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=False,
                )
