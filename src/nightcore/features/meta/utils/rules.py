"""Utilities for parsing and handling legal clauses."""

from typing import Any

from discord import Color, Embed

from src.config.config import config
from src.infra.db.models._annot import Chapter, Rule, Rules


def parse_clause(clause: str) -> list[int]:
    """Parse a clause string into a list of integers."""
    try:
        indexes = [int(x) for x in clause.strip().split(".")]
        if not indexes or any(x <= 0 for x in indexes):
            return []
        return indexes
    except ValueError:
        return []


def build_rules_embeds(title: str, text_lines: list[str]) -> list[list[Embed]]:
    """Builds a list of lists of embeds from the given title and text lines."""
    embeds: list[list[Embed]] = []
    current_embeds: list[Embed] = [
        Embed(
            title=title,
            color=Color.blue(),
        )
    ]
    current_text = ""
    total_length = 0

    def flush_current():
        """Flush the current text into the last embed."""
        nonlocal current_text, current_embeds
        if current_text.strip():
            current_embeds[-1].description = (
                "```css\n" + current_text.strip() + "\n```"
            )
            current_text = ""

    for line in text_lines:
        line_with_nl = line + "\n"
        line_len = len(line_with_nl)
        if total_length + line_len > config.bot.EMBED_DESCRIPTION_LIMIT:
            flush_current()
            embeds.append(current_embeds)
            current_embeds = [
                Embed(
                    color=Color.blurple(),
                )
            ]
            total_length = 0

            if (
                len(current_text) + line_len
                > config.bot.EMBED_DESCRIPTION_LIMIT
            ):
                flush_current()
                current_embeds.append(
                    Embed(
                        color=Color.blue(),
                    )
                )
            total_length += len("```css\n") + len("\n```")

        current_text += line_with_nl
        total_length += line_len

    flush_current()
    if current_embeds:
        embeds.append(current_embeds)

    return embeds


"""
parse_clause("2.3") -> [2, 3]
parse_clause("1") -> [1]
"""


def convert_dict_to_rules(data: dict[str, Any]) -> Rules:
    """Convert a dictionary to a Rules object."""
    if not data or not data.get("chapters"):
        return Rules(chapters=[])

    rules = Rules(
        chapters=[
            Chapter(
                number=c["number"],
                title=c["title"],
                rules=[
                    Rule(
                        number=r["number"],
                        text=r["text"],
                        subrules=[Rule(**sr) for sr in r.get("subrules", [])],
                    )
                    for r in c["rules"]
                ],
            )
            for c in data["chapters"]
        ]
    )

    return rules
