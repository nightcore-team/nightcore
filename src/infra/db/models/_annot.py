from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from src.infra.db.models import (
        ChangeStat,
        NotifyState,
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
    notifications: list[NotifyState]
    total_messages: int = 0


class ModerationStatsResultAnnot(TypedDict):
    moderators: dict[int, str]
    punishments: Sequence[Punish]
    tickets: Sequence[TicketState]
    role_requests: Sequence[RoleRequestState]
    changestats: Sequence[ChangeStat]
    notifications: Sequence[NotifyState]
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

    type: int
    drop_id: int
    name: str
    amount: int
    chance: int
    is_color_compensation: bool | None


class FAQPageAnnot(TypedDict):
    title: str
    description: str
    content: str
    image_url: str | None


class BattlepassRewardAnnot(TypedDict):
    """Battlepass reward configuration."""

    type: int
    drop_id: int
    name: str
    amount: int
    is_color_compensation: bool | None


class BattlepassLevelAnnot(TypedDict):
    """Battlepass level configuration."""

    level: int
    exp_required: int
    reward: BattlepassRewardAnnot


class CasinoBetAnnot(TypedDict):
    user_id: int
    bet: int
    selected_color: str
    result_coins: int | None
