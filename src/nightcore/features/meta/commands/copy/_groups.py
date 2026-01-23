from discord import app_commands

copy = app_commands.Group(
    name="copy",
    description="Commands for copying",
    guild_only=True,
)
