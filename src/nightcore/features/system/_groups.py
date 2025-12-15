from discord import app_commands

system = app_commands.Group(
    name="system",
    description="Системны команды и настройки",
    guild_only=True,
)

config = app_commands.Group(
    name="config",
    description="Настройки систем Nightcore",
    guild_only=True,
    parent=system,
)
