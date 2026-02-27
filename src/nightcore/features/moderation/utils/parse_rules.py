"""Utilities for parsing and finding rules in a structured ruleset."""

from src.infra.db.models._annot import Chapter, Rule, Rules


def parse_clause(v: str) -> bool:
    """Check if the clause string is valid (non-empty and contains only positive integers separated by dots)."""  # noqa: E501
    return not (
        not v or any(not x.isdigit() or int(x) <= 0 for x in v.split("."))
    )


def find_rule_by_index(
    rules: Rules, index: str
) -> tuple[Rule | Chapter | None, str | None]:
    """Find a rule or chapter by its index in the rules structure and return the item with its canonical index string.

    Returns:
        (item, "i" or "i.j" or "i.j.k") if found, otherwise None.
    """  # noqa: E501
    try:
        parts = [int(p) for p in index.strip().split(".") if p != ""]
    except ValueError:
        return None, None

    # level 1 - chapter
    if len(parts) == 1:
        chapter_idx0 = parts[0] - 1
        if 0 <= chapter_idx0 < len(rules.chapters):
            chapter = rules.chapters[chapter_idx0]
            return chapter, f"{chapter_idx0 + 1}"
        return None, None

    # level 2 - rule
    chapter_idx0 = parts[0] - 1
    if not (0 <= chapter_idx0 < len(rules.chapters)):
        return None, None

    chapter = rules.chapters[chapter_idx0]
    rule_idx0 = parts[1] - 1
    if not (0 <= rule_idx0 < len(chapter.rules)):
        return None, None

    rule = chapter.rules[rule_idx0]

    # level 3 - subrule
    if len(parts) == 3:
        sub_idx0 = parts[2] - 1
        if 0 <= sub_idx0 < len(rule.subrules):
            subrule = rule.subrules[sub_idx0]
            return (
                subrule,
                f"{chapter_idx0 + 1}.{rule_idx0 + 1}.{sub_idx0 + 1}",
            )
        return None, None

    # exactly level 2
    if len(parts) == 2:
        return rule, f"{chapter_idx0 + 1}.{rule_idx0 + 1}"

    # unsupported depth
    return None, None
