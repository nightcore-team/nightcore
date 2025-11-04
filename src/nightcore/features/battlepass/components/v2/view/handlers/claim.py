"""
Battlepass claim reward button handler.

Handles claiming battlepass reward and updating the view accordingly.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction
from sqlalchemy.orm import attributes

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_or_create_user
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.services.config import specified_guild_config

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

    from ..claim import BattlepassClaimViewV2

logger = logging.getLogger(__name__)


async def handle_battlepass_claim_reward_button(
    interaction: Interaction["Nightcore"],
    view_to_update: type["BattlepassClaimViewV2"],
) -> None:
    """Handle battlepass claim reward button."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    outcome = ""
    new_level = 0
    new_points = 0
    reward_name = ""
    reward_amount = 0
    coin_name = "коинов"

    await interaction.response.defer(ephemeral=True)

    async with specified_guild_config(bot, guild.id, GuildEconomyConfig) as (
        guild_config,
        session,
    ):
        coin_name = guild_config.coin_name or "коинов"

        user_record, _ = await get_or_create_user(
            session, guild_id=guild.id, user_id=interaction.user.id
        )

        battlepass_rewards = guild_config.battlepass_rewards or []

        if not battlepass_rewards:
            outcome = "battlepass_not_configured"
        else:
            current_level_data = None
            for bp_level in battlepass_rewards:
                if bp_level["level"] == user_record.battle_pass_level:
                    current_level_data = bp_level
                    break

            if current_level_data is None:
                outcome = "level_not_found"
            else:
                required_points = current_level_data["exp_required"]

                if user_record.battle_pass_points < required_points:
                    outcome = "not_enough_points"
                else:
                    reward = current_level_data["reward"]
                    reward_type = reward["name"]
                    reward_amount = reward["amount"]

                    match reward_type:
                        case "coins":
                            user_record.coins += reward_amount
                            reward_name = f"{reward_amount} {coin_name}"

                        case "coins_case" | "colors_case":
                            if reward_type in user_record.inventory["cases"]:
                                user_record.inventory["cases"][
                                    reward_type  # type: ignore
                                ] += reward_amount
                            else:
                                user_record.inventory["cases"][reward_type] = (  # type: ignore
                                    reward_amount
                                )

                            attributes.flag_modified(user_record, "inventory")
                            reward_name = f"{reward_amount} кейсов с коинами"

                        case "exp":
                            user_record.current_exp += reward_amount
                            reward_name = f"{reward_amount} опыта"

                        case _:
                            outcome = "unknown_reward_type"

                    if not outcome:
                        overflow_points = (
                            user_record.battle_pass_points - required_points
                        )
                        user_record.battle_pass_level += 1
                        user_record.battle_pass_points = overflow_points

                        new_level = user_record.battle_pass_level
                        new_points = overflow_points

                        outcome = "success"

                        logger.info(
                            "[battlepass] User %s claimed level %s reward (%s) in guild %s",  # noqa: E501
                            interaction.user.id,
                            current_level_data["level"],
                            reward_name,
                            guild.id,
                        )

    if outcome == "battlepass_not_configured":
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка получения награды",
                "Баттлпас не настроен на этом сервере.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if outcome == "level_not_found":
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка получения награды",
                "Ваш текущий уровень не найден в конфигурации баттлпаса.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if outcome == "not_enough_points":
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Недостаточно опыта",
                "У вас недостаточно опыта для получения награды за этот уровень.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if outcome == "unknown_reward_type":
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка получения награды",
                "Неизвестный тип награды. Обратитесь к администрации.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if outcome == "success":
        updated_view = view_to_update(
            bot=bot,
            level=new_level,
            total_levels=len(battlepass_rewards),
            current_points=new_points,
            required_points=battlepass_rewards[new_level - 1][  # type: ignore
                "exp_required"
            ],
            reward_type=reward_type,  # type: ignore
            reward_amount=reward_amount,
            avatar_url=interaction.user.display_avatar.url,
        )

        await asyncio.gather(
            interaction.followup.edit_message(
                message_id=interaction.message.id,  # type: ignore
                view=updated_view,
            ),
            interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Награда получена",
                    f"Вы получили награду за уровень {new_level - 1}: {reward_name}.",  # noqa: E501
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            ),
        )
