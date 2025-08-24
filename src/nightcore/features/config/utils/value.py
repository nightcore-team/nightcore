"""Utility functions for parsing configuration values related to roles in Nightcore."""  # noqa

from src.nightcore.features.config.exceptions import (
    LevelRolesParsingError,
    OrgRolesParsingError,
    TempVoiceRolesParsingError,
)
from src.nightcore.utils.field_validators import (
    FieldSpec,
    ValueKind,
    parse_str_parts,
)


def _to_org_roles(s: str | None):
    """Converts a list of parts into a roles specification."""

    parts = parse_str_parts(s)
    result: dict[str, dict[str, str | int]] = {}

    for part in parts:
        if len(part) != 3:
            raise OrgRolesParsingError("Expected 3 parts: name, tag, role_id")
        name, tag, role_id_raw = part
        if not name or not tag:
            raise OrgRolesParsingError("Name and tag cannot be empty")
        try:
            role_id = int(role_id_raw)
        except ValueError as e:
            raise OrgRolesParsingError(
                f"Invalid role ID: {role_id_raw}"
            ) from e

        result[tag.upper()] = {"name": name, "role_id": role_id}

    return result


def _to_level_roles(s: str | None):
    parts = parse_str_parts(s)
    result: dict[int, int] = {}

    for part in parts:
        if len(part) != 2:
            raise LevelRolesParsingError("Expected 2 parts: level, role_id")
        level_raw, role_id_raw = part
        if not any((level_raw, role_id_raw)):
            raise LevelRolesParsingError("Level and role ID cannot be empty")
        try:
            level = int(level_raw)
        except ValueError as e:
            raise LevelRolesParsingError(f"Invalid level: {level_raw}") from e
        try:
            role_id = int(role_id_raw)
        except ValueError as e:
            raise LevelRolesParsingError(
                f"Invalid role ID: {role_id_raw}"
            ) from e

        result[level] = role_id

    return result


def _to_temp_voice_roles(s: str | None):
    parts = parse_str_parts(s)
    result: dict[int, int] = {}

    for part in parts:
        if len(part) != 2:
            raise TempVoiceRolesParsingError(
                "Expected 2 parts: voice_id, role_id"
            )
        voice_id_raw, role_id_raw = part
        if not any((voice_id_raw, role_id_raw)):
            raise TempVoiceRolesParsingError(
                "Voice ID and role ID cannot be empty"
            )
        try:
            voice_id = int(voice_id_raw)
        except ValueError as e:
            raise TempVoiceRolesParsingError(
                f"Invalid voice ID: {voice_id_raw}"
            ) from e
        try:
            role_id = int(role_id_raw)
        except ValueError as e:
            raise TempVoiceRolesParsingError(
                f"Invalid role ID: {role_id_raw}"
            ) from e

        result[voice_id] = role_id

    return result


def org_roles_dict_value(field: str, value: str | None) -> FieldSpec | None:
    """Creates a FieldSpec for a roles dictionary from a string representation."""  # noqa: E501
    if value is None:
        return None

    return FieldSpec(
        field=field,
        value=value,
        kind=ValueKind.DICT,
        transform=_to_org_roles,
    )


def level_roles_dict_value(field: str, value: str | None) -> FieldSpec | None:
    """Creates a FieldSpec for a roles dictionary from a string representation."""  # noqa: E501
    if value is None:
        return None

    return FieldSpec(
        field=field,
        value=value,
        kind=ValueKind.DICT,
        transform=_to_level_roles,
    )


def temp_voice_roles_dict_value(
    field: str, value: str | None
) -> FieldSpec | None:
    """Creates a FieldSpec for a roles dictionary from a string representation."""  # noqa: E501
    if value is None:
        return None

    return FieldSpec(
        field=field,
        value=value,
        kind=ValueKind.DICT,
        transform=_to_temp_voice_roles,
    )
