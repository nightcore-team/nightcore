"""Groups for the configuration commands."""

from discord import app_commands

config = app_commands.Group(
    name="config",
    description="Configuration commands for the Nightcore bot.",
)
logging = app_commands.Group(
    name="logging",
    description="Configuration commands for the logging.",
    parent=config,
)
moderation = app_commands.Group(
    name="moderation",
    description="Configuration commands for the moderation.",
    parent=config,
)
economy = app_commands.Group(
    name="economy",
    description="Configuration commands for the economy.",
    parent=config,
)
