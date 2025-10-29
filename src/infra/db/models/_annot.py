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


class CasesAnnot(TypedDict): ...


class ColorsAnnot(TypedDict): ...


class UserInventoryAnnot(TypedDict):
    cases: CasesAnnot
    colors: ColorsAnnot


class CoinDropAnnot(TypedDict):
    """Single coin drop configuration."""

    amount: int
    chance: float


class ColorDropAnnot(TypedDict):
    """Single color drop configuration."""

    name: str
    role_id: int
    chance: float
