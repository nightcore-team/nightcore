"""Utility functions and classes for handling configuration values in Nightcore."""  # noqa

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class ValueKind(Enum):
    INT = auto()
    FLOAT = auto()
    STR = auto()
    LIST_INT = auto()
    LIST_STR = auto()
    DICT = auto()


@dataclass
class FieldSpec:
    field: str
    value: Any
    kind: ValueKind
    transform: Callable[[Any], Any] | None = None
    skip_if_none: bool = True


@dataclass
class Change:
    field: str
    old: Any
    new: Any
    changed: bool
    kind: ValueKind


# parsing / transformations


def _to_id(obj: Any) -> int:
    """Extracts an integer ID from an object."""
    return obj.id


def _parse_csv_ints(s: str | None) -> list[int] | None:
    """Parses a comma-separated string of integers into a list of integers."""
    if not s:
        return None
    out: list[int] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out or None


def parse_str_parts(s: str | None) -> list[list[str]]:
    """Parses a string into a list of parts, splitting by commas and pipes."""
    if not s:
        return []
    return [
        parts
        for seg in s.split("|")
        if (parts := [f for f in (p.strip() for p in seg.split(",")) if f])
    ]


# values


def int_id_value(field: str, obj: Any | None) -> FieldSpec | None:
    """Creates a FieldSpec for an integer ID."""
    if obj is None:
        return None

    if isinstance(obj, int):
        return FieldSpec(field=field, value=obj, kind=ValueKind.INT)

    if hasattr(obj, "id"):
        return FieldSpec(
            field=field, value=obj, kind=ValueKind.INT, transform=_to_id
        )

    raise TypeError(
        f"int_id(): unsupported type for field {field}: {type(obj)!r}"
    )


def float_value(field: str, value: float | int | None) -> FieldSpec | None:
    """Creates a FieldSpec for a float value."""
    if value is None:
        return None

    return FieldSpec(
        field=field, value=value, kind=ValueKind.FLOAT, transform=float
    )


def str_value(field: str, value: str | None) -> FieldSpec | None:
    """Creates a FieldSpec for a string value."""
    if value is None:
        return None

    return FieldSpec(
        field=field, value=value, kind=ValueKind.STR, transform=str
    )


def list_csv(field: str, csv: str | None) -> FieldSpec | None:
    """Creates a FieldSpec for a list of integers from a comma-separated string."""  # noqa: E501
    parsed = _parse_csv_ints(csv)
    if parsed is None:
        return None

    return FieldSpec(field=field, value=parsed, kind=ValueKind.LIST_INT)
