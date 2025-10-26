"""Utility functions for logging and summarizing Discord app commands."""

from collections.abc import Iterable
from logging import Logger
from typing import Any, cast

from discord import app_commands


def walk_group(
    group: app_commands.Group, prefix: str = ""
) -> Iterable[tuple[str, app_commands.AppCommand]]:
    """Recursively walks through a command group and yields tuples of command names and their objects."""  # noqa: E501
    for cmd in group.commands:
        if isinstance(cmd, app_commands.Group):
            yield (f"{prefix}{cmd.name}", cmd)  # type: ignore
            # рекурсія
            yield from walk_group(cmd, prefix=f"{prefix}{cmd.name} ")  # type: ignore
        else:
            yield (f"{prefix}{cmd.name}", cmd)  # type: ignore


def summarize_tree(tree: app_commands.CommandTree) -> dict[str, str | Any]:
    """
    Returns summary information about the command tree.
    {
        "top_level_total": N,
        "top_level": [
            {
                "name": "config",
                "type": "group",
                "children_total": M,
                "leaf_total": L,
                "children": [
                    { "qualified": "config logging setup", "type": "leaf" },
                    ...
                ]
            },
            {
                "name": "ping",
                "type": "leaf"
            },
            ...
        ],
        "leaf_overall": X   # total number of leaf commands (excluding groups)
    }.
    """  # noqa: D205
    result = {
        "top_level_total": 0,
        "top_level": [],
        "leaf_overall": 0,
    }
    top_cmds = tree.get_commands()
    result["top_level_total"] = len(top_cmds)

    overall_leaf = 0

    for top in top_cmds:
        if isinstance(top, app_commands.Group):
            entries: list[dict[str, Any]] = []
            leaf_count = 0
            for qname, obj in walk_group(top, prefix=f"{top.name} "):  # type: ignore
                if isinstance(obj, app_commands.Group):
                    entries.append(
                        {
                            "qualified": qname.strip(),
                            "type": "group",
                            "children_count": len(
                                getattr(obj, "commands", [])
                            ),
                        }
                    )
                else:
                    entries.append(
                        {
                            "qualified": qname.strip(),
                            "type": "leaf",
                            "binding": getattr(
                                obj, "binding", None
                            ).__class__.__name__
                            if getattr(obj, "binding", None)
                            else None,  # для інфо
                        }
                    )
                    leaf_count += 1
            overall_leaf += leaf_count
            cast(list, result["top_level"]).append(
                {
                    "name": top.name,  # type: ignore
                    "type": "group",
                    "children_total": len(top.commands),
                    "leaf_total": leaf_count,
                    "children": entries,
                }
            )
        else:
            cast(list[str], result["top_level"]).append(
                {"name": top.name, "type": "leaf", "qualified": top.name}  # type: ignore
            )
            overall_leaf += 1

    result["leaf_overall"] = overall_leaf

    return result


def log_tree_summary(
    tree: app_commands.CommandTree, *, logger: Logger
) -> None:
    """Formatted log."""
    data = summarize_tree(tree)
    logger.info(
        "Slash tree summary: top_level_total=%s leaf_overall=%s",
        data["top_level_total"],
        data["leaf_overall"],
    )

    for entry in data["top_level"]:
        if entry["type"] == "leaf":
            logger.info("  /%s (leaf)", entry["name"])
        else:
            logger.info(
                "  /%s (group) children=%s leaf=%s",
                entry["name"],
                entry["children_total"],
                entry["leaf_total"],
            )
            for child in entry["children"]:
                if child["type"] == "group":
                    logger.info(
                        "     - %s (subgroup, children=%s)",
                        child["qualified"],
                        child["children_count"],
                    )
                else:
                    logger.info(
                        "     - %s (command, binding=%s)",
                        child["qualified"],
                        child["binding"],
                    )
