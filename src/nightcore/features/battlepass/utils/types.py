"""Types used in Battlepass feature."""

from typing import Final

from discord import app_commands

BATTLEPASS_REWARDS: Final[dict[str, str]] = {
    "coins_case": "Кейс с коинами",
    "colors_case": "Кейс с цветами",
    "coins": "коины",
    "exp": "опыт",
}


BATTLEPASS_REWARDS_CHOICES: Final[list[app_commands.Choice[str]]] = [
    *[
        app_commands.Choice(name=v, value=k)
        for k, v in BATTLEPASS_REWARDS.items()
    ]
]
