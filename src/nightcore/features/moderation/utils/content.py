"""Utils for parsing needed text from components."""

import logging
import re
from typing import cast

import regex
from discord import Component

logger = logging.getLogger(__name__)


def parse_inactive_text_from_components(
    components: list[Component],
) -> str | None:  # type: ignore
    """Extracts the form text from a list of components."""
    for container in components:
        for item in container.children:  # type: ignore
            if item.id == 5:  # type: ignore
                content = cast(str | None, item.content)  # type: ignore
                if content:
                    return content.replace("```", "").strip()

    return None


def parse_author_id_from_components(components: list[Component]):  # type: ignore
    """Extracts the author ID from a list of components."""
    for component in components:
        for item in component.children:  # type: ignore
            if item.id == 3:  # type: ignore
                match = re.search(r"<@!?(\d+)>", item.content)  # type: ignore
                if match:
                    return int(match.group(1))

    return None


def parse_nickname_from_components(components: list[Component]) -> str | None:  # type: ignore
    """Extracts the nickname from a list of components.

    Expected message format (inside a code block)::

        1. Ник: {nickname}
        2. Дата отпуска/неактива: {date_range}
        3. Причина: {reason}
        4. Уведомили ли вы своего дискорд мастера?: {Да/Нет}

    The function is tolerant of surrounding backticks and whitespace and
    supports both Cyrillic `Ник` and Latin `Nick` labels.
    """

    text = parse_inactive_text_from_components(components)
    if not text:
        return None

    text = text.strip()
    # remove triple-backtick code fences if present
    if text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()

    # Try to match numbered line like "1. Ник: value"
    match = re.search(
        r"^\s*\d+\.\s*(?:Ник|Nick):\s*(.+)$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if match:
        return match.group(1).strip()

    # Fallback: look for any "Ник: value" or "Nick: value" anywhere
    match = re.search(
        r"(?:Ник|Nick):\s*(\S(?:.*?))(?=\n|$)", text, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()

    return None


def remove_emoji_from_text(text: str) -> str:
    """Removes custom emojis from the text."""

    return regex.sub(r"\p{Emoji}", "", text)
