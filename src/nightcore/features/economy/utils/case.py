"""Utilities for handling cases opening in the economy feature."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.models.battlepass_level import BattlepassLevel
from src.infra.db.models.guild import GuildEconomyConfig
from src.infra.db.models.user import UserCase
from src.infra.db.operations import (
    get_case_by_id,
    get_color_by_id,
    get_specified_guild_config,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from discord import Guild
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.infra.db.models._annot import BattlepassRewardAnnot, CaseDropAnnot
    from src.infra.db.models.case import Case
    from src.infra.db.models.user import User


class RewardOutcomeEnum(Enum):
    SUCCESS = 0
    UNKNOWN_REWARD = 1
    REWARD_NOT_FOUND = 2
    COLOR_WITH_COMPENSATION = 3


async def give_reward_by_type(
    session: AsyncSession,
    *,
    reward: CaseDropAnnot | BattlepassRewardAnnot,
    user: User,
) -> RewardOutcomeEnum:
    """Apply reward to user based on reward type and return outcome status."""

    drop_id = reward["drop_id"]
    amount = reward["amount"]

    match reward["type"]:
        case CaseDropTypeEnum.EXP.value:
            user.current_exp += amount
        case CaseDropTypeEnum.COINS.value:
            user.coins += amount
        case CaseDropTypeEnum.BATTLEPASS_POINTS.value:
            user.battle_pass_points += amount
        case CaseDropTypeEnum.COLOR.value:
            color = await get_color_by_id(
                session, guild_id=user.guild_id, color_id=drop_id
            )

            if color is None:
                return RewardOutcomeEnum.REWARD_NOT_FOUND

            if user.get_color(color.id) is None:
                user.colors.append(color)
            else:
                guild_config = await get_specified_guild_config(
                    session,
                    config_type=GuildEconomyConfig,
                    guild_id=user.guild_id,
                )

                compensation = (
                    guild_config.color_drop_compensation if guild_config else 0
                )

                user.coins += compensation

                reward["type"] = CaseDropTypeEnum.COINS.value
                reward["amount"] = compensation

                return RewardOutcomeEnum.COLOR_WITH_COMPENSATION

        case CaseDropTypeEnum.CASE.value:
            case = await get_case_by_id(
                session, guild_id=user.guild_id, case_id=drop_id
            )

            if case is None:
                return RewardOutcomeEnum.REWARD_NOT_FOUND

            if (user_case := user.get_case(case.id)) is not None:
                user_case.amount += amount
            else:
                new_case = UserCase(
                    user_id=user.user_id, case_id=case.id, amount=amount
                )
                session.add(new_case)

        case CaseDropTypeEnum.CUSTOM.value:
            ...
        case _:
            return RewardOutcomeEnum.UNKNOWN_REWARD

    return RewardOutcomeEnum.SUCCESS


async def format_cases_rewards(
    session: AsyncSession,
    *,
    cases: Sequence[Case],
    coin_name: str,
    guild: Guild,
):
    """Resolve and format case drop names (modifies objects in-place)."""

    for case in cases:
        for drop in case.drop:
            match drop["type"]:
                case CaseDropTypeEnum.COINS.value:
                    drop["name"] = coin_name
                case CaseDropTypeEnum.CASE.value:
                    case = await get_case_by_id(
                        session, guild_id=guild.id, case_id=drop["drop_id"]
                    )

                    drop["name"] = case.name if case else "unknown"
                case CaseDropTypeEnum.COLOR.value:
                    color = await get_color_by_id(
                        session, guild_id=guild.id, color_id=drop["drop_id"]
                    )

                    if color is None:
                        drop["name"] = "unknown"
                    else:
                        role = guild.get_role(color.role_id)
                        drop["name"] = role.name if role else "unknown"
                case _:
                    ...


async def format_battlepass_levels_rewards(
    session: AsyncSession,
    *,
    levels: Sequence[BattlepassLevel],
    coin_name: str,
    guild: Guild,
):
    """Resolve and format battlepass reward names (modifies objects in-place)."""  # noqa: E501

    for level in levels:
        match level.reward["type"]:
            case CaseDropTypeEnum.COINS.value:
                level.reward["name"] = coin_name
            case CaseDropTypeEnum.CASE:
                case = await get_case_by_id(
                    session, guild_id=guild.id, case_id=level.reward["drop_id"]
                )

                level.reward["name"] = case.name if case else "unknown"
            case CaseDropTypeEnum.COLOR.value:
                color = await get_color_by_id(
                    session,
                    guild_id=guild.id,
                    color_id=level.reward["drop_id"],
                )

                if color is None:
                    level.reward["name"] = "unknown"
                else:
                    role = guild.get_role(color.role_id)
                    level.reward["name"] = role.name if role else "unknown"
            case _:
                ...
