"""Utility functions for validating user input in role requests."""


def validate_user_nickname(nickname: str) -> str | None:
    """Validate the user's nickname format."""
    if not nickname or "_" not in nickname:
        return None

    parts = nickname.split("_")
    if len(parts) != 2 or not all(part.isalpha() for part in parts):
        return None

    return nickname
