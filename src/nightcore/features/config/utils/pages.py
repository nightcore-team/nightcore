"""Utility functions for formatting guild configuration data."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.config.config import config as project_config

if TYPE_CHECKING:
    from src.infra.db.operations import GuildT


def build_guild_config_pages(
    config: GuildT,
    is_v2: bool = False,
    fields_per_page: int = 25,
) -> list[str]:
    """Format the guild configuration into paginated description pages.

    Args:
        config: The guild configuration object.
        is_v2: Whether to use v2 description limit.
        fields_per_page: Maximum number of fields per page.

    Returns:
        List of paginated strings with guild configuration.
    """

    limit = project_config.bot.EMBED_DESCRIPTION_LIMIT

    if is_v2:
        limit = project_config.bot.VIEW_V2_DESCRIPTION_LIMIT

    pages: list[str] = []
    current = ""
    fields_in_current_page = 0

    for field in config.__table__.columns:
        field_name = field.name
        if field_name == "id":
            continue

        field_value = getattr(config, field_name)

        if isinstance(field_value, dict):
            field_value = ", ".join(
                f"{k}: {v}"
                for k, v in field_value.items()  # type: ignore
            )

        if isinstance(field_value, list):
            field_value = ", ".join(str(item) for item in field_value)  # type: ignore

        if field_value is None:
            field_value = "Не установлено"

        if not field_value:
            field_value = "Не установлено"

        line = f"**{field_name}**: {field_value}\n"

        if (len(current) + len(line) >= limit) or (
            fields_in_current_page >= fields_per_page
        ):
            pages.append(current)
            current = ""
            fields_in_current_page = 0

        current += line
        fields_in_current_page += 1

    if current:
        pages.append(current)

    if not pages:
        pages = ["Конфигурация сервера не настроена."]

    return pages
