from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

from src.infra.db.models._enums import CaseDropTypeEnum

if TYPE_CHECKING:
    from src.infra.db.models import (
        ChangeStat,
        Punish,
        RoleRequestState,
        TicketState,
    )


class OrgRoleWithoutTagAnnot(TypedDict):
    name: str
    role_id: int


@dataclass
class ModerationInfractionsDataAnnot:
    nickname: str
    punishments: list[Punish]
    tickets: list[TicketState]
    role_requests: list[RoleRequestState]
    changestats: list[ChangeStat]
    total_messages: int = 0


class ModerationStatsResultAnnot(TypedDict):
    moderators: dict[int, str]
    punishments: Sequence[Punish]
    tickets: Sequence[TicketState]
    role_requests: Sequence[RoleRequestState]
    changestats: Sequence[ChangeStat]
    messages: dict[int, int]


@dataclass
class Rules:
    chapters: list[Chapter]


@dataclass
class Chapter:
    number: int
    title: str
    rules: list[Rule]


@dataclass
class Rule:
    number: str
    text: str
    subrules: list[Rule]


class CaseDropAnnot(TypedDict):
    """Single drop configuration."""

    type: CaseDropTypeEnum
    drop_id: int | None
    name: str
    amount: int
    chance: int


class FAQPageAnnot(TypedDict):
    title: str
    description: str
    content: str
    image_url: str | None


class BattlepassRewardAnnot(TypedDict):
    """Battlepass reward configuration."""

    type: int
    drop_id: int | None
    name: str
    amount: int


class BattlepassLevelAnnot(TypedDict):
    """Battlepass level configuration."""

    level: int
    exp_required: int
    reward: BattlepassRewardAnnot
