"""Handlers for pending case opening rerolls."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from discord import Guild, Member
from discord.interactions import Interaction

from src.infra.db.operations import (
    get_case_by_id,
    get_case_open_rewards_for_update,
    get_case_open_session_for_update,
    get_user_for_update,
)
from src.nightcore.components.view.v2 import ErrorViewV2
from src.nightcore.features.economy.components.v2 import build_case_reroll_view
from src.nightcore.features.economy.utils.case import format_single_case_reward
from src.utils._enums import CaseOpenSessionStatus

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


async def handle_case_open_reroll(
    interaction: Interaction["Nightcore"],
    *,
    session_id: int,
    reward_id: int,
    page: int,
) -> None:
    """Reroll one pending case reward."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    member = cast(Member, interaction.user)

    await interaction.response.defer(ephemeral=True)

    view_data: dict[str, Any] | None = None

    async with bot.uow.start() as session:
        case_session = await get_case_open_session_for_update(
            session, session_id=session_id
        )
        if case_session is None or case_session.user_id != member.id:
            outcome = "not_found"
        elif case_session.status != CaseOpenSessionStatus.PENDING:
            outcome = "closed"
        elif case_session.expires_at <= datetime.now(UTC):
            outcome = "expired"
        else:
            user = await get_user_for_update(
                session,
                guild_id=guild.id,
                user_id=member.id,
                for_update=True,
            )
            reward_rows = await get_case_open_rewards_for_update(
                session,
                session_id=session_id,
                reward_id=reward_id,
            )
            case = await get_case_by_id(
                session,
                guild_id=guild.id,
                case_id=case_session.case_id,
            )

            if user is None or not reward_rows or case is None:
                outcome = "not_found"
            elif user.rerolls < (
                reroll_cost := 2 ** reward_rows[0].reroll_count
            ):
                outcome = "no_rerolls"
            else:
                generated = case.open(amount=1)
                reward = generated[0] if generated else None
                if reward is None:
                    outcome = "error"
                else:
                    await format_single_case_reward(
                        session,
                        drops=[reward],
                        coin_name=None,
                        guild=guild,
                    )
                    reward_rows[0].reward = reward
                    reward_rows[0].reroll_count += 1
                    user.rerolls -= reroll_cost
                    case_session.rerolls_used += reroll_cost

                    view_data = {
                        "case_name": case.name,
                        "total_weight": sum(
                            drop["chance"] for drop in case.drop
                        ),  # type: ignore
                        "rewards": [
                            {
                                **dict(row.reward),
                                "reward_id": row.id,
                                "rerolls_used": row.reroll_count,
                            }
                            for row in reward_rows
                        ],
                        "rerolls_left": user.rerolls,
                    }
                    outcome = "success"

    if outcome == "success":
        if view_data is None:
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка реролла",
                    "Данные сесии открытия не найдены.",
                ),
                ephemeral=True,
            )
            return

        view = build_case_reroll_view(
            bot,
            session_id=session_id,
            current_page=page,
            **view_data,
        )
        await interaction.followup.edit_message(
            interaction.message.id,  # type: ignore
            view=view,
        )
        return

    if outcome == "not_found":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка реролла",
                "Сессия открытия кейса не найдена.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "closed":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка реролла",
                "Эта сессия открытия уже завершена.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "expired":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка реролла",
                "Срок действия сессии открытия истёк.",
            ),
            ephemeral=True,
        )
        return

    if outcome == "no_rerolls":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка реролла",
                f"Недостаточно рероллов (требуется {reroll_cost}).",  # type: ignore
            ),
            ephemeral=True,
        )
        return

    if outcome == "error":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка реролла",
                "Не удалось сгенерировать новую награду.",
            ),
            ephemeral=True,
        )
        return
