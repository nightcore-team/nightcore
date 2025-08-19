"""Utilities for managing configuration updates in Nightcore."""

from collections.abc import Sequence
from typing import Any, Literal

from .value import Change, FieldSpec, ValueKind


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
            except Exception as e:
                raise e
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
