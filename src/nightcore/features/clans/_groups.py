"""Groups for the clans commands."""

from discord import app_commands

clan = app_commands.Group(
    name="clan",
    description="Commands for clans.",
)

manage = app_commands.Group(
    name="manage",
    description="Commands to manage your clan.",
    parent=clan,
)
