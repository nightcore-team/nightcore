from dataclasses import dataclass
from typing import TypedDict


class OrgRoleWithoutTagAnnot(TypedDict):
    name: str
    role_id: int


@dataclass
class Rules:
    chapters: list["Chapter"]


@dataclass
class Chapter:
    number: int
    title: str
    rules: list["Rule"]


@dataclass
class Rule:
    number: str
    text: str
    subrules: list["Rule"]


class CasesAnnot(TypedDict):
    """{"case_name": amount}."""


class ColorsAnnot(TypedDict):
    """["color_name"]."""


class UserInventoryAnnot(TypedDict):
    cases: CasesAnnot
    colors: list[str]


class CoinDropAnnot(TypedDict):
    """Single coin drop configuration."""

    amount: int
    chance: int


class ColorDropAnnot(TypedDict):
    """Single color drop configuration."""

    role_id: int
    chance: int


class FAQPageAnnot(TypedDict):
    title: str
    description: str
    content: str


class BattlepassRewardAnnot(TypedDict):
    """Battlepass reward configuration."""

    name: str
    amount: int


class BattlepassLevelAnnot(TypedDict):
    """Battlepass level configuration."""

    level: int
    exp_required: int
    reward: BattlepassRewardAnnot
