"""Utility functions for formatting guild configuration data."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.config.config import config as project_config

if TYPE_CHECKING:
    from src.infra.db.operations import GuildT


def _format_config_value(field_name: str, value: object) -> str:
    """Format config values while preserving structure and pinging IDs."""

    if value is None:
        return "Не установлено"

    if isinstance(value, dict):
        if not value:
            return "Не установлено"

        return ", ".join(
            f"{_format_config_value(field_name, key)}: {_format_config_value(field_name, item)}"  # type: ignore  # noqa: E501
            for key, item in value.items()  # type: ignore
        )

    if isinstance(value, list):
        if not value:
            return "Не установлено"

        return ", ".join(
            _format_config_value(field_name, item)  # type: ignore
            for item in value  # type: ignore
        )

    if isinstance(value, bool):
        return str(value)

    if isinstance(value, int):
        if field_name.endswith(
            ("_channel_id", "_channel_ids", "_category_id", "_category_ids")
        ):
            return f"<#{value}>"

        if (
            field_name.endswith(("_role_id", "_roles_ids"))
            or "role" in field_name
        ):
            return f"<@&{value}>"

    text = str(value)
    if not text:
        return "Не установлено"

    return text


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

        line = f"**{field_name}**: {_format_config_value(field_name, field_value)}\n"  # noqa: E501

        if current and (
            (len(current) + len(line) >= limit)
            or (fields_in_current_page >= fields_per_page)
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
