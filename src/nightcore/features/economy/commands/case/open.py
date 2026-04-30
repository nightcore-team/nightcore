"""Command to open case."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.models.guild import GuildEconomyConfig
from src.infra.db.operations import (
    get_or_create_user,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    ValidationErrorEmbed,
)
from src.nightcore.features.economy._groups import case as case_group
from src.nightcore.features.economy.components.v2 import CaseOpenViewV2
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.features.economy.utils import user_cases_autocomplete
from src.nightcore.features.economy.utils.case import (
    RewardOutcomeEnum,
    format_single_case_reward,
    give_reward_by_type,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@case_group.command(name="open", description="Открыть кейс")  # type: ignore
@app_commands.describe(
    case_id="Кейс для открытия.",
    amount="Количество кейсов для открытия (по умолчанию 1).",
)
@app_commands.rename(case_id="case")
@app_commands.autocomplete(case_id=user_cases_autocomplete)
@check_required_permissions(PermissionsFlagEnum.NONE)
async def open_case(
    interaction: Interaction["Nightcore"],
    case_id: app_commands.Transform[int, StrToIntTransformer],
    amount: int = 1,
):
    """Open case and get reward."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    outcome = ""
    reward_text = ""
    logging_channel_id = None
    opened_case_item = None

    try:
        async with specified_guild_config(
            bot, guild.id, config_type=GuildEconomyConfig
        ) as (guild_config, session):
            user, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=member.id,
                with_relations=True,
            )

            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

            user_case = user.get_case(case_id)

            if user_case is None:
                outcome = "no_case"
            else:
                opened_case_item = user_case.item
                if amount > 1 and user_case.amount < amount:
                    outcome = "no_many_cases"
                else:
                    rewards = opened_case_item.open(amount=amount)

                    if not rewards or all(
                        reward is None for reward in rewards
                    ):
                        outcome = "no_case_reward_configured"
                    else:
                        user_case.amount -= amount

                        result = await give_reward_by_type(
                            session,
                            rewards=rewards,  # pyright: ignore[reportArgumentType]
                            user=user,
                        )

                        is_color_compensation = (
                            result == RewardOutcomeEnum.COLOR_WITH_COMPENSATION
                        )

                        await format_single_case_reward(
                            session,
                            drops=rewards,  # pyright: ignore[reportArgumentType]
                            coin_name=guild_config.coin_name,
                            guild=guild,
                            is_color_compensation=is_color_compensation,
                        )

                        reward_text = ", ".join(
                            reward["name"]  # type: ignore
                            for reward in rewards
                        )

                        outcome = (
                            "success"
                            if result == RewardOutcomeEnum.SUCCESS
                            or result
                            == RewardOutcomeEnum.COLOR_WITH_COMPENSATION
                            else "error: " + result.name
                        )

    except Exception as e:
        logger.exception(
            "[case/open] Error opening case %s for user %s in guild %s: %s",
            case_id,
            member.id,
            guild.id,
            e,
        )
        outcome = "error"

    if outcome == "no_case":
        return await interaction.response.send_message(
            embed=ValidationErrorEmbed(
                "У вас нет такого кейса для открытия.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "no_case_reward_configured":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка открытия кейса",
                "Награды не настроены для выбранного кейса.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome.startswith("error"):
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка открытия кейса",
                f"Произошла ошибка при открытии кейса. {outcome}",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        if opened_case_item is None:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка открытия кейса",
                    "Кейс не найден после открытия.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        view = CaseOpenViewV2(
            bot=bot,
            case_name=opened_case_item.name,
            total_weight=sum(drop["chance"] for drop in opened_case_item.drop),  # type: ignore
            opened_amount=amount,
            rewards=rewards,  # type: ignore
        )
        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )
        aggregated_to_dispatch = {}
        for r in rewards:  # type: ignore
            r_name = r["name"]  # type: ignore
            if r_name not in aggregated_to_dispatch:
                aggregated_to_dispatch[r_name] = {"amount": 0}
            aggregated_to_dispatch[r_name]["amount"] += r["amount"]  # type: ignore

        for r_name, val in aggregated_to_dispatch.items():  # type: ignore
            bot.dispatch(
                "user_items_changed",
                dto=AwardNotificationEventDTO(
                    guild=guild,
                    event_type="case/open",
                    logging_channel_id=logging_channel_id,
                    user_id=member.id,
                    moderator_id=bot.user.id,  # type: ignore
                    item_name=r_name,  # type: ignore
                    amount=val["amount"],  # type: ignore
                    reason=f"открытие кейса (x{amount})"
                    if amount > 1
                    else "открытие кейса",
                ),
            )

    logger.info(
        "[command] - invoked user=%s guild=%s case=%s reward=%s",
        member.id,
        case_id,
        guild.id,
        reward_text,
    )
