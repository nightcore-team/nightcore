"""Utilities for handling cases opening in the economy feature."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.db.models._annot import CaseDropAnnot
from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.models.user import User


async def give_reward_by_type(
    session: AsyncSession, *, reward: CaseDropAnnot, user: User
):
    match reward["type"]:
        case CaseDropTypeEnum.EXP:
            user.current_exp += reward["amount"]
        case CaseDropTypeEnum.COINS:
            user.coins += reward["amount"]
        case CaseDropTypeEnum.COLOR:
            ...
        case CaseDropTypeEnum.CASE:
            ...
        case CaseDropTypeEnum.CUSTOM:
            ...
        case _:
            ...
