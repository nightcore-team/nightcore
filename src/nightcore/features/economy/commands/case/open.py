"""Command to open case."""

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.loads import user_load_cases_and_colors
from src.infra.db.models import GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.operations import (
    create_case_open_session,
    get_case_open_rewards_for_update,
    get_or_create_user,
    get_pending_case_open_session,
    get_specified_webhook,
)
from src.nightcore.components.view.v2 import ErrorViewV2, ValidationErrorViewV2
from src.nightcore.features.economy._groups import case as case_group
from src.nightcore.features.economy.components.v2 import (
    CaseOpenViewV2,
    build_case_reroll_view,
)
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.features.economy.utils import user_cases_autocomplete
from src.nightcore.features.economy.utils.case import (
    format_single_case_reward,
    give_reward_by_type,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer
from src.utils._enums import ChannelType

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
    logging_webhook = None
    opened_case_item = None
    pending_view_data: dict[str, Any] | None = None

    try:
        async with specified_guild_config(
            bot, guild.id, config_type=GuildEconomyConfig
        ) as (guild_config, session):
            user, _ = await get_or_create_user(
                session,
                guild_id=guild.id,
                user_id=member.id,
                options=user_load_cases_and_colors,
                for_update=True,
            )

            pending_session = await get_pending_case_open_session(
                session,
                guild_id=guild.id,
                user_id=member.id,
            )

            if pending_session is not None:
                outcome = "pending_session"

            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

            user_case = user.get_case(case_id) if not outcome else None

            if not outcome:
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

                            if user.rerolls > 0:
                                await format_single_case_reward(
                                    session,
                                    drops=rewards,  # pyright: ignore[reportArgumentType]
                                    coin_name=guild_config.coin_name,
                                    guild=guild,
                                )
                                pending_session = (
                                    await create_case_open_session(
                                        session,
                                        guild_id=guild.id,
                                        user_id=member.id,
                                        case_id=case_id,
                                        expires_at=datetime.now(UTC)
                                        + timedelta(minutes=5),
                                        rewards=rewards,  # type: ignore
                                    )
                                )
                                reward_rows = (
                                    await get_case_open_rewards_for_update(
                                        session,
                                        session_id=pending_session.id,
                                    )
                                )
                                pending_view_data = {
                                    "session_id": pending_session.id,
                                    "case_name": opened_case_item.name,
                                    "total_weight": sum(
                                        drop["chance"]
                                        for drop in opened_case_item.drop
                                    ),  # type: ignore
                                    "rewards": [
                                        {
                                            **dict(row.reward),
                                            "reward_id": row.id,
                                        }
                                        for row in reward_rows
                                    ],
                                    "rerolls_left": user.rerolls,
                                }
                            else:
                                result = await give_reward_by_type(
                                    session,
                                    rewards=rewards,  # type: ignore
                                    user=user,
                                )

                                await format_single_case_reward(
                                    session,
                                    drops=result[0],  # type: ignore
                                    coin_name=guild_config.coin_name,
                                    guild=guild,
                                )

                            reward_text = ", ".join(
                                reward["name"]  # type: ignore
                                for reward in rewards
                            )

                            outcome = "success"

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
        await interaction.response.send_message(
            view=ValidationErrorViewV2(
                "У вас нет такого кейса для открытия.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "pending_session":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Открытие кейса уже ожидает решения",
                "Сначала завершите предыдущую сессию открытия кейса.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "no_case_reward_configured":
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка открытия кейса",
                "Награды не настроены для выбранного кейса.",
            ),
            ephemeral=True,
        )
        return

    if outcome.startswith("error"):
        await interaction.response.send_message(
            view=ErrorViewV2(
                "Ошибка открытия кейса",
                "Произошла ошибка при открытии кейса.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "success":
        if opened_case_item is None:
            await interaction.response.send_message(
                view=ErrorViewV2(
                    "Ошибка открытия кейса",
                    "Кейс не найден после открытия.",
                ),
                ephemeral=True,
            )
            return

        if pending_view_data is not None:
            await interaction.response.send_message(
                view=build_case_reroll_view(
                    bot,
                    **pending_view_data,
                ),
                ephemeral=False,
            )
            return

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
                    logging_webhook=logging_webhook,
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
