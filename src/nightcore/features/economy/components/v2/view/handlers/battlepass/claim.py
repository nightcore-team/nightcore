"""
Battlepass claim reward button handler.

Handles claiming battlepass reward and updating the view accordingly.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any, cast

from discord import Guild, Member
from discord.interactions import Interaction

from src.infra.db.loads import user_load_cases_colors_and_vips
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
from src.nightcore.features.economy.utils.vip import get_user_active_vip_ids
from src.nightcore.services.config import specified_guild_config
from src.utils._enums import ChannelType

if TYPE_CHECKING:
    from src.infra.db.models.battlepass_level import BattlepassLevel
    from src.nightcore.bot import Nightcore

    from ...battlepass.claim import BattlepassClaimViewV2

logger = logging.getLogger(__name__)


def _vip_limit_error_view() -> ErrorViewV2:
    """Error shown when a VIP reward can't be given over MAX_USER_VIPS."""

    return ErrorViewV2(
        "Ошибка получения награды",
        "Достигнуто максимальное количество VIP-статусов, награда не "
        "может быть выдана.\n> Дождитесь окончания одного из VIP-статусов "
        "и попробуйте снова.",
    )


def build_additional_reward_view_data(
    level_data: "BattlepassLevel",
    *,
    user_vip_ids: list[int],
    claimed_level: int | None,
    show_level: int,
) -> dict[str, Any]:
    """Build additional reward params for the battlepass claim view."""

    additional_reward = level_data.additional_reward or {}

    return {
        "additional_reward_type": additional_reward.get("name"),
        "additional_reward_amount": additional_reward.get("amount"),
        "additional_reward_access_vip_id": additional_reward.get(
            "vip_id_access"
        ),
        "user_vip_ids": user_vip_ids,
        "additional_reward_claimed": (
            claimed_level is not None and claimed_level >= show_level
        ),
    }


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
            options=user_load_cases_colors_and_vips,
            for_update=True,
        )

        user_vip_ids = await get_user_active_vip_ids(
            session, guild_id=guild.id, user_id=user_record.id
        )
        claimed_additional_level = (
            user_record.battle_pass_additional_reward_claimed_level
        )

        battlepass_levels = await get_guild_battlepass_levels(
            session, guild_id=guild.id
        )

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

                    if RewardOutcomeEnum.VIP_LIMIT_REACHED in result:
                        outcome = "vip_limit_reached"
                    elif (
                        RewardOutcomeEnum.COLOR_WITH_COMPENSATION not in result
                        and RewardOutcomeEnum.SUCCESS not in result
                    ):
                        if result[0] == RewardOutcomeEnum.UNKNOWN_REWARD:
                            outcome = "unknown_reward"
                        elif result[0] == RewardOutcomeEnum.REWARD_NOT_FOUND:
                            outcome = "reward_not_found"

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

    if outcome == "vip_limit_reached":
        await interaction.followup.send(
            view=_vip_limit_error_view(), ephemeral=True
        )
        return

    if outcome in ("reward_not_found", "unknown_reward"):
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка при получении награды",
                "Награда не была найдена на сервере или является неизвестной.\n> Уведомите руководство о данной ошибке для дальнейшего изменения награды.",  # noqa: E501
            ),
            ephemeral=True,
        )
        return

    if outcome == "success" or outcome == "success_no_next_level":
        async with bot.uow.start() as session:
            await format_single_battlepass_level_reward(
                session,
                level=new_level_data,  # type: ignore
                coin_name=guild_config.coin_name,
                guild=guild,
            )

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
            **build_additional_reward_view_data(
                new_level_data,  # type: ignore
                user_vip_ids=user_vip_ids,
                claimed_level=claimed_additional_level,
                show_level=new_level,
            ),
        )

        success_message = f"Вы получили награду за уровень {claimed_level}."

        if outcome == "success_no_next_level":
            success_message += (
                "\n> Вы достигли максимального уровня баттлпаса."
            )

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

        if logging_webhook is not None:
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


async def handle_battlepass_claim_additional_reward_button(
    interaction: Interaction["Nightcore"],
    view_to_update: type["BattlepassClaimViewV2"],
) -> None:
    """Handle battlepass additional reward claim button."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    user = cast(Member, interaction.user)

    outcome = ""
    reward_name = ""
    additional_view_data: dict[str, Any] | None = None

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
            options=user_load_cases_colors_and_vips,
            for_update=True,
        )

        user_vip_ids = await get_user_active_vip_ids(
            session, guild_id=guild.id, user_id=user_record.id
        )

        battlepass_levels = await get_guild_battlepass_levels(
            session, guild_id=guild.id
        )

        logging_webhook = await get_specified_webhook(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_ECONOMY,
        )

        if len(battlepass_levels) < 1:
            outcome = "battlepass_not_configured"
        else:
            if user_record.battle_pass_level > len(battlepass_levels):
                outcome = "level_not_found"
            else:
                current_level_data = battlepass_levels[
                    user_record.battle_pass_level - 1
                ]

                claimed_level = (
                    user_record.battle_pass_additional_reward_claimed_level
                )

                if (
                    claimed_level is not None
                    and claimed_level >= user_record.battle_pass_level
                ):
                    outcome = "already_claimed"
                else:
                    reward = current_level_data.additional_reward
                    access_vip_id = (
                        reward.get("vip_id_access") if reward else None
                    )

                    # the view only hides the button, and it is built from
                    # the state at render time, so the access and the points
                    # are checked here again against the locked user row
                    if not reward:
                        outcome = "no_additional_reward"
                    elif (
                        access_vip_id is None
                        or access_vip_id not in user_vip_ids
                    ):
                        outcome = "no_vip_access"
                    elif (
                        user_record.battle_pass_points
                        < current_level_data.exp_required
                    ):
                        outcome = "not_enough_points"
                    else:
                        reward["is_color_compensation"] = None

                        _, result = await give_reward_by_type(
                            session, rewards=[reward], user=user_record
                        )

                        if RewardOutcomeEnum.VIP_LIMIT_REACHED in result:
                            outcome = "vip_limit_reached"
                        elif (
                            RewardOutcomeEnum.COLOR_WITH_COMPENSATION
                            not in result
                            and RewardOutcomeEnum.SUCCESS not in result
                        ):
                            outcome = "error"
                        else:
                            user_record.battle_pass_additional_reward_claimed_level = (  # noqa: E501
                                user_record.battle_pass_level
                            )
                            claimed_level = user_record.battle_pass_level

                            reward_name = reward["name"]

                            logger.info(
                                "[battlepass] User %s claimed additional reward (%s) for level %s in guild %s",  # noqa: E501
                                interaction.user.id,
                                reward_name,
                                user_record.battle_pass_level,
                                guild.id,
                            )

                            additional_view_data = (
                                build_additional_reward_view_data(
                                    current_level_data,
                                    user_vip_ids=user_vip_ids,
                                    claimed_level=claimed_level,
                                    show_level=user_record.battle_pass_level,
                                )
                            )

                            outcome = "success"

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

    if outcome == "already_claimed":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Награда уже получена",
                "Дополнительная награда за этот уровень уже была получена.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "no_additional_reward":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка получения награды",
                "Дополнительная награда не настроена для этого уровня.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "no_vip_access":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка получения награды",
                "Дополнительная награда доступна только с активным "
                "VIP-статусом, который для неё требуется.",
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

    if outcome == "vip_limit_reached":
        await interaction.followup.send(
            view=_vip_limit_error_view(), ephemeral=True
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

    if outcome == "success":
        if additional_view_data is None:
            return

        async with bot.uow.start() as session:
            await format_single_battlepass_level_reward(
                session,
                level=current_level_data,  # type: ignore
                coin_name=guild_config.coin_name,
                guild=guild,
            )

        updated_view = view_to_update(
            bot=bot,
            level=user_record.battle_pass_level,
            total_levels=len(battlepass_levels),
            current_points=user_record.battle_pass_points,
            required_points=current_level_data.exp_required,  # type: ignore
            reward_type=current_level_data.reward["name"],  # type: ignore
            reward_amount=current_level_data.reward["amount"],  # type: ignore
            avatar_url=interaction.user.display_avatar.url,
            **additional_view_data,
        )

        await asyncio.gather(
            interaction.followup.edit_message(
                message_id=interaction.message.id,  # type: ignore
                view=updated_view,
            ),
            interaction.followup.send(
                view=SuccessViewV2(
                    "Награда получена",
                    f"Вы получили дополнительную награду за уровень "
                    f"{user_record.battle_pass_level}.",
                ),
                ephemeral=True,
            ),
        )

        if logging_webhook is not None:
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
                    reason="Дополнительная награда /battlepass",
                ),
            )
