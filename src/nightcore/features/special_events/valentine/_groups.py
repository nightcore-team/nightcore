from discord import app_commands

valentine = app_commands.Group(
    name="valentine",
    description="Commands related to St. Valentine's Day event",
    guild_only=True,
)
