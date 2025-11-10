"""Command to play casino roulette game."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_or_create_user
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.economy._groups import casino as casino_group
from src.nightcore.features.economy.components.v2 import RouletteViewV2
from src.nightcore.features.economy.utils.casino import (
    RouletteColor,
    RouletteResult,
    spin_roulette,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@casino_group.command(name="roulette", description="Сыграть в рулетку")  # type: ignore
@app_commands.describe(
    bet="Ваша ставка (минимум 5 коинов)", color="Выберите цвет"
)
@app_commands.choices(
    color=[
        app_commands.Choice(name="🔴 Красное (x2)", value="red"),
        app_commands.Choice(name="⚫ Чёрное (x2)", value="black"),
        app_commands.Choice(name="🟢 Зелёное (x14)", value="green"),
    ]
)
@app_commands.checks.cooldown(1, 15.0, key=lambda i: i.user.id)
@check_required_permissions(PermissionsFlagEnum.NONE)
async def roulette(
    interaction: Interaction["Nightcore"],
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

    async with specified_guild_config(
        bot, guild_id=guild.id, config_type=GuildEconomyConfig
    ) as (guild_config, session):
        try:
            user, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=member.id,
            )

            if user.coins < bet:
                outcome = "insufficient_balance"
            else:
                number, spin_color = spin_roulette()
                result = RouletteResult(
                    number, spin_color, bet, selected_color
                )

                guild_config.last_roulette_games.append(spin_color)

                if len(guild_config.last_roulette_games) > 10:
                    guild_config.last_roulette_games = (
                        guild_config.last_roulette_games[-10:]
                    )

                attributes.flag_modified(guild_config, "last_roulette_games")

                user.coins += result.coins_change

                outcome = "success"

                logger.info(
                    "[roulette] User %s bet %d on %s, got %d (%s), %s %d coins in guild %s",  # noqa: E501
                    member.id,
                    bet,
                    selected_color,
                    number,
                    spin_color,
                    "won" if result.is_win else "lost",
                    abs(result.coins_change),
                    guild.id,
                )

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

    if outcome == "success" and result:
        coin_name = guild_config.coin_name or "коинов"

        view = RouletteViewV2(
            bot=bot,
            coin_name=coin_name,
            last_roulette_games=guild_config.last_roulette_games,
            result=result,
            new_balance=user.coins,  # type: ignore
        )

        return await interaction.response.send_message(
            view=view, ephemeral=True
        )

    logger.info(
        "[command] - invoked user=%s guild=%s result=%s",
        interaction.user.id,
        guild.id,
        str(result),
    )
