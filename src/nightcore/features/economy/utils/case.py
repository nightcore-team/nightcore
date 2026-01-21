"""Utilities for handling cases opening in the economy feature."""

from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models._annot import BattlepassRewardAnnot, CaseDropAnnot
from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.models.user import User, UserCase
from src.infra.db.operations import get_case_by_id, get_color_by_id


class RewardOutcomeEnum(Enum):
    SUCCESS = 0
    UNKNOWN_REWARD = 1
    REWARD_NOT_FOUND = 2


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
        case CaseDropTypeEnum.EXP:
            user.current_exp += amount
        case CaseDropTypeEnum.COINS:
            user.coins += amount
        case CaseDropTypeEnum.BATTLEPASS_POINTS:
            user.battle_pass_points += amount
        case CaseDropTypeEnum.COLOR:
            if drop_id is None:
                return RewardOutcomeEnum.REWARD_NOT_FOUND

            color = await get_color_by_id(
                session, guild_id=user.guild_id, color_id=drop_id
            )

            if color is None:
                return RewardOutcomeEnum.REWARD_NOT_FOUND

            if user.get_color(color.id) is None:
                user.colors.append(color)

        case CaseDropTypeEnum.CASE:
            if drop_id is None:
                return RewardOutcomeEnum.REWARD_NOT_FOUND

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

        case CaseDropTypeEnum.CUSTOM:
            ...
        case _:
            return RewardOutcomeEnum.UNKNOWN_REWARD

    return RewardOutcomeEnum.SUCCESS
