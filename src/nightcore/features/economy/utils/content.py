"""Content related utils for economy system."""


def safe_split_wallet_id(choice: str) -> int | None:
    """Parse "extra:<id>" into the wallet id.

    Returns None if `choice` doesn't have the expected shape or the id
    part isn't a valid int — e.g. a user bypassed autocomplete and typed
    garbage directly into the option.
    """
    if not choice:
        return None

    parts = choice.split(":", 1)
    if len(parts) != 2:
        return None

    _, raw_id = parts
    if not raw_id:
        return None

    try:
        return int(raw_id)
    except ValueError:
        return None
