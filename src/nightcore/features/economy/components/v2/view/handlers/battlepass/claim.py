"""
Battlepass claim reward button handler.

Handles claiming battlepass reward and updating the view accordingly.
"""

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.operations import (
    get_guild_battlepass_levels,
    get_or_create_user,
    get_specified_webhook,
)
from src.nightcore.components.view.v2 import ErrorViewV2, SuccessViewV2
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.features.economy.utils.case import (
    RewardOutcomeEnum,
    format_single_battlepass_level_reward,
    give_reward_by_type,
)
from src.nightcore.services.config import specified_guild_config
from src.utils._enums import ChannelType

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

    from ...battlepass.claim import BattlepassClaimViewV2

logger = logging.getLogger(__name__)


async def handle_battlepass_claim_reward_button(
    interaction: Interaction["Nightcore"],
    view_to_update: type["BattlepassClaimViewV2"],
) -> None:
    """Handle battlepass claim reward button."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    user = cast(Member, interaction.user)

    outcome = ""
    new_level = 0
    new_points = 0
    reward_name = ""
    disable_button = False
    claimed_level = 0
    # Keep references for second tx handling
    battlepass_levels_snapshot = None  # type: ignore
    new_level_data_snapshot = None  # type: ignore
    guild_config_snapshot = None  # type: ignore

    await interaction.response.defer(ephemeral=True)

    async with specified_guild_config(
        bot, guild_id=guild.id, config_type=GuildEconomyConfig
    ) as (
        guild_config,
        session,
    ):
        user_record, _ = await get_or_create_user(
            session,
            guild_id=guild.id,
            user_id=interaction.user.id,
            with_relations=True,
            for_update=True,
        )

        battlepass_levels = await get_guild_battlepass_levels(
            session, guild_id=guild.id
        )
        # snapshot for later use after session closes
        battlepass_levels_snapshot = battlepass_levels
        guild_config_snapshot = guild_config

        logging_webhook = await get_specified_webhook(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_ECONOMY,
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
                    reward["is_color_compensation"] = None

                    _, result = await give_reward_by_type(
                        session, rewards=[reward], user=user_record
                    )

                    if (
                        RewardOutcomeEnum.COLOR_WITH_COMPENSATION not in result
                        and RewardOutcomeEnum.SUCCESS not in result
                    ):
                        outcome = "error"

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

                        # snapshot after determining new level
                        new_level_data_snapshot = new_level_data
                        # Atomic formatting: try to format inside same tx
                        # so failure rolls back reward. If formatting fails,
                        # we will handle second tx fallback, but at least
                        # we attempt atomic formatting here.
                        try:
                            await format_single_battlepass_level_reward(
                                session,
                                level=new_level_data,  # type: ignore
                                coin_name=guild_config.coin_name,
                                guild=guild,
                            )
                        except Exception as fmt_exc:
                            logger.warning(
                                "[battlepass] Formatting inside claim tx "
                                "failed for guild %s level %s: %s",
                                guild.id,
                                new_level,
                                fmt_exc,
                            )
                            # Do not rollback reward for formatting failure;  # noqa: E501
                            # second tx will handle fallback. Keep outcome success.  # noqa: E501

                        logger.info(
                            "[battlepass] User %s claimed level %s reward (%s) in guild %s",  # noqa: E501
                            interaction.user.id,
                            claimed_level,
                            reward_name,
                            guild.id,
                        )

    if outcome == "battlepass_not_configured":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка получения награды",
                "Баттлпас не настроен на этом сервере.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "level_not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка получения награды",
                "Ваш текущий уровень не найден в конфигурации баттлпаса.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "not_enough_points":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Недостаточно опыта",
                "У вас недостаточно опыта для получения награды за этот уровень.",  # noqa: E501
            ),
            ephemeral=True,
        )
        return

    if outcome.startswith("error"):
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка при получении награды",
                "Произошла ошибка при получении награды.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "success" or outcome == "success_no_next_level":
        # Second transaction was previously separate and could fail after  # noqa: E501
        # claim committed. Handle failure gracefully to avoid inconsistent  # noqa: E501
        # view state. Use readonly transaction for pure formatting reads.  # noqa: E501
        try:
            async with bot.uow.start(readonly=True) as session:
                await format_single_battlepass_level_reward(
                    session,
                    level=new_level_data_snapshot,  # type: ignore
                    coin_name=guild_config_snapshot.coin_name,  # type: ignore
                    guild=guild,
                )
        except Exception as e:
            logger.error(
                "[battlepass] Failed to format reward for guild %s level %s: %s",  # noqa: E501
                guild.id,
                new_level,
                e,
                exc_info=True,
            )
            # Fallback: ensure reward has a name so view doesn't crash
            try:
                snap_reward = new_level_data_snapshot.reward  # type: ignore
                if not snap_reward.get("name"):
                    r_type = snap_reward.get("type")
                    if r_type == "coins":
                        snap_reward["name"] = (
                            guild_config_snapshot.coin_name or "коины"  # type: ignore
                        )
                    elif r_type == "case":
                        snap_reward["name"] = "кейс"
                    elif r_type == "color":
                        snap_reward["name"] = "цвет"
                    else:
                        snap_reward["name"] = "награда"
            except Exception:
                pass

        # If formatting still not ok but reward missing name, view will use  # noqa: E501
        # fallback above. new_level_data is guaranteed to exist here  # noqa: E501
        # (snapshot from first tx)
        updated_view = view_to_update(
            bot=bot,
            level=new_level,
            total_levels=len(battlepass_levels_snapshot),  # type: ignore
            current_points=new_points,
            required_points=new_level_data_snapshot.exp_required,  # type: ignore
            reward_type=new_level_data_snapshot.reward["name"],  # type: ignore
            reward_amount=new_level_data_snapshot.reward["amount"],  # type: ignore
            avatar_url=interaction.user.display_avatar.url,
            disable_button=disable_button,
        )

        success_message = f"Вы получили награду за уровень {claimed_level}."

        if outcome == "success_no_next_level":
            success_message += (
                "\n> Вы достигли максимального уровня баттлпаса."
            )

        try:
            await asyncio.gather(
                interaction.followup.edit_message(
                    message_id=interaction.message.id,  # type: ignore
                    view=updated_view,
                ),
                interaction.followup.send(
                    view=SuccessViewV2(
                        "Награда получена",
                        success_message,
                    ),
                    ephemeral=True,
                ),
            )
        except Exception as view_exc:
            logger.error(
                "[battlepass] Failed to update view after claim for guild %s user %s: %s",  # noqa: E501
                guild.id,
                user.id,
                view_exc,
                exc_info=True,
            )
            # As a fallback, at least send success message if edit failed
            with contextlib.suppress(Exception):  # type: ignore
                await interaction.followup.send(
                    view=SuccessViewV2(
                        "Награда получена",
                        success_message,
                    ),
                    ephemeral=True,
                )

        if logging_webhook is not None:
            try:
                bot.dispatch(
                    "user_items_changed",
                    dto=AwardNotificationEventDTO(
                        guild=guild,
                        event_type="give_coins",
                        logging_webhook=logging_webhook,
                        user_id=user.id,
                        moderator_id=interaction.user.id,
                        item_name=reward["name"],  # type: ignore
                        amount=reward["amount"],  # type: ignore
                        reason="Награда /battlepass",
                    ),
                )
            except Exception as dispatch_exc:
                logger.error(
                    "[battlepass] Failed to dispatch award notification: %s",
                    dispatch_exc,
                )
