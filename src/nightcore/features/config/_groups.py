"""Groups for the configuration commands."""

from discord import app_commands

config = app_commands.Group(
    name="config",
    description="Команды конфигурации для бота Nightcore.",
    guild_only=True,
)

battlepass = app_commands.Group(
    name="battlepass",
    description="Команды конфигурации для боевого пропуска.",
    parent=config,
    guild_only=True,
)
