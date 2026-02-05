"""
Battlepass claim reward button handler.

Handles claiming battlepass reward and updating the view accordingly.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from discord import Guild
from discord.interactions import Interaction

from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.models.guild import GuildEconomyConfig
from src.infra.db.operations import (
    get_case_by_id,
    get_color_by_id,
    get_guild_battlepass_levels,
    get_or_create_user,
)
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.economy.utils.case import (
    RewardOutcomeEnum,
    give_reward_by_type,
)
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
    coin_name = ""
    disable_button = False
    claimed_level = 0

    await interaction.response.defer(ephemeral=True)

    async with specified_guild_config(
        bot, guild_id=guild.id, config_type=GuildEconomyConfig
    ) as (
        guild_config,
        session,
    ):
        coin_name = guild_config.coin_name if guild_config else "коины"

        user_record, _ = await get_or_create_user(
            session, guild_id=guild.id, user_id=interaction.user.id
        )

        battlepass_levels = await get_guild_battlepass_levels(
            session, guild_id=guild.id
        )

        if len(battlepass_levels) < 1:
            outcome = "battlepass_not_configured"
        else:
            if len(battlepass_levels) < user_record.battle_pass_level:
                outcome = "level_not_found"
            else:
                current_level_data = battlepass_levels[
                    user_record.battle_pass_level - 1
                ]

                required_points = current_level_data.exp_required

                if user_record.battle_pass_points < required_points:
                    outcome = "not_enough_points"
                else:
                    reward = current_level_data.reward

                    result = await give_reward_by_type(
                        session, reward=reward, user=user_record
                    )

                    if result != RewardOutcomeEnum.SUCCESS:
                        outcome = "error: " + result.name

                    if not outcome:
                        overflow_points = (
                            user_record.battle_pass_points - required_points
                        )
                        claimed_level = user_record.battle_pass_level
                        user_record.battle_pass_points = overflow_points

                        user_record.battle_pass_level += 1

                        new_level = user_record.battle_pass_level
                        new_points = overflow_points

                        if (
                            len(battlepass_levels)
                            < user_record.battle_pass_level
                        ):
                            # New level not found, show previous level
                            # with disabled button
                            outcome = "success_no_next_level"

                            disable_button = True

                            new_level_data = battlepass_levels[
                                user_record.battle_pass_level - 2
                            ]
                        else:
                            new_level_data = battlepass_levels[
                                user_record.battle_pass_level - 1
                            ]

                            new_level = user_record.battle_pass_level

                            outcome = "success"

                        logger.info(
                            "[battlepass] User %s claimed level %s reward (%s) in guild %s",  # noqa: E501
                            interaction.user.id,
                            claimed_level,
                            reward_name,
                            guild.id,
                        )

    if outcome == "battlepass_not_configured":
        await interaction.followup.send(
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
        await interaction.followup.send(
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
        await interaction.followup.send(
            embed=ErrorEmbed(
                "Недостаточно опыта",
                "У вас недостаточно опыта для получения награды за этот уровень.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if outcome.startswith("error"):
        await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка при получении награды",
                f"Произошла ошибка при получении награды. {outcome}",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if outcome == "success" or outcome == "success_no_next_level":
        match new_level_data.reward["type"]:  # type: ignore
            case CaseDropTypeEnum.COINS.value:
                new_level_data.reward["name"] = coin_name or "коины"  # type: ignore
            case CaseDropTypeEnum.CASE.value:
                case = await get_case_by_id(
                    session,
                    guild_id=guild.id,
                    case_id=new_level_data.reward["drop_id"],  # type: ignore
                )

                new_level_data.reward["name"] = (  # type: ignore
                    case.name if case else "unknown"
                )
            case CaseDropTypeEnum.COLOR.value:
                color = await get_color_by_id(
                    session,
                    guild_id=guild.id,
                    color_id=new_level_data.reward["drop_id"],  # type: ignore
                )

                if color is None:
                    reward_name = "unknown"
                else:
                    role = guild.get_role(color.role_id)

                    reward_name = role.name if role else "unknown"

            case _:
                ...

        # new_level_data is guaranteed to exist here
        updated_view = view_to_update(
            bot=bot,
            level=new_level,
            total_levels=len(battlepass_levels),
            current_points=new_points,
            required_points=new_level_data.exp_required,  # type: ignore
            reward_type=new_level_data.reward["name"],  # type: ignore
            reward_amount=new_level_data.reward["amount"],  # type: ignore
            avatar_url=interaction.user.display_avatar.url,
            disable_button=disable_button,
        )

        success_message = f"Вы получили награду за уровень {claimed_level}."

        if outcome == "success_no_next_level":
            success_message += (
                "\n\nВы достигли максимального уровня баттлпаса."
            )

        await asyncio.gather(
            interaction.followup.edit_message(
                message_id=interaction.message.id,  # type: ignore
                view=updated_view,
            ),
            interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Награда получена",
                    success_message,
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            ),
        )
