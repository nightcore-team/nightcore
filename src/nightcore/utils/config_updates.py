"""Utilities for managing configuration updates in Nightcore."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Literal


class ValueKind(Enum):
    INT = auto()
    FLOAT = auto()
    STR = auto()
    LIST_INT = auto()
    LIST_STR = auto()


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
    # Role, Channel, Category, Thread, Message etc.
    return obj.id


def _parse_csv_ints(s: str | None) -> list[int] | None:
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


# helpers for FieldSpec


def int_id(field: str, obj: Any | None) -> FieldSpec | None:
    """Creates a FieldSpec for an integer ID, or returns None if the object is None."""  # noqa: E501
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
    if value is None:
        return None

    return FieldSpec(
        field=field, value=value, kind=ValueKind.FLOAT, transform=float
    )


def str_value(field: str, value: str | None) -> FieldSpec | None:
    if value is None:
        return None

    return FieldSpec(
        field=field, value=value, kind=ValueKind.STR, transform=str
    )


def list_csv(field: str, csv: str | None) -> FieldSpec | None:
    parsed = _parse_csv_ints(csv)
    if parsed is None:
        return None

    return FieldSpec(field=field, value=parsed, kind=ValueKind.LIST_INT)


def list_ids(field: str, objs: Sequence[Any] | None) -> FieldSpec | None:
    if not objs:
        return None
    ids = []
    for o in objs:
        if hasattr(o, "id"):
            ids.append(o.id)
        elif isinstance(o, int):
            ids.append(o)
        else:
            raise TypeError(f"list_ids(): unsupported element {o!r}")

    return FieldSpec(field=field, value=ids, kind=ValueKind.LIST_INT)


def list_int(field: str, values: Sequence[int] | None) -> FieldSpec | None:
    if not values:
        return None

    return FieldSpec(field=field, value=list(values), kind=ValueKind.LIST_INT)


def apply_field_changes(
    model: Any, specs: Sequence[FieldSpec]
) -> list[Change]:
    """Applies field changes to a model based on provided specifications."""
    results: list[Change] = []
    for spec in specs:
        if spec.skip_if_none and spec.value is None:
            continue

        new_raw = spec.value
        if spec.transform:
            try:
                new_val = spec.transform(new_raw)
            except Exception:
                continue
        else:
            new_val = new_raw

        # current value in model
        old_val = getattr(model, spec.field, None)

        # normalize for lists: to be type-insensitive (tuple vs list)
        if spec.kind in (ValueKind.LIST_INT, ValueKind.LIST_STR):
            # convert to list
            old_comp = [] if old_val is None else list(old_val)
            new_comp = list(new_val)
            changed = old_comp != new_comp
            if changed:
                setattr(model, spec.field, new_comp)
            results.append(
                Change(
                    field=spec.field,
                    old=old_comp,
                    new=new_comp,
                    changed=changed,
                    kind=spec.kind,
                )
            )
            continue

        # simple types
        changed = old_val != new_val
        if changed:
            setattr(model, spec.field, new_val)

        results.append(
            Change(
                field=spec.field,
                old=old_val,
                new=new_val,
                changed=changed,
                kind=spec.kind,
            )
        )
    return results


# embed
def split_changes(
    changes: Sequence[Change],
) -> tuple[list[Change], list[Change]]:
    """Splits changes into updated and skipped."""
    updated = [c for c in changes if c.changed]
    skipped = [c for c in changes if not c.changed]
    return updated, skipped


def format_changes(
    updated: Sequence[Change], skipped: Sequence[Change]
) -> str:
    """Formats the changes for display."""
    parts: list[str] = []
    if updated:
        parts.append(
            "Updated:\n"
            + "\n".join(
                f"- {c.field} (old={c.old!r} new={c.new!r})" for c in updated
            )
        )
    if skipped:
        parts.append(
            "Unchanged / skipped:\n"
            + "\n".join(f"- {c.field}" for c in skipped)
        )
    if not parts:
        return "Nothing changed."
    return "\n\n".join(parts)


def update_id_list(
    current: Sequence[int] | None,
    value: int,
    action: Literal["add", "remove"],
) -> tuple[list[int], bool, str]:
    """Updates a list of IDs by adding or removing a value."""
    ids = list(current or [])
    if action == "add":
        if value in ids:
            return ids, False, "exists"
        ids.append(value)
        return ids, True, "added"
    else:  # remove
        if value not in ids:
            return ids, False, "absent"
        ids = [x for x in ids if x != value]
        return ids, True, "removed"
