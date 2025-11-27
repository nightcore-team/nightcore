"""Groups for the configuration commands."""

from discord import app_commands

config = app_commands.Group(
    name="config",
    description="Команды конфигурации для бота Nightcore.",
    guild_only=True,
)
other = app_commands.Group(
    name="other",
    description="Команды конфигурации для других настроек.",
    parent=config,
    guild_only=True,
)
logging = app_commands.Group(
    name="logging",
    description="Команды конфигурации для логирования.",
    parent=config,
    guild_only=True,
)
moderation = app_commands.Group(
    name="moderation",
    description="Команды конфигурации для модерации.",
    parent=config,
    guild_only=True,
)

economy = app_commands.Group(
    name="economy",
    description="Команды конфигурации для экономики.",
    parent=config,
    guild_only=True,
)

levels = app_commands.Group(
    name="levels",
    description="Команды конфигурации для уровней.",
    parent=config,
    guild_only=True,
)

clans = app_commands.Group(
    name="clans",
    description="Команды конфигурации для кланов.",
    parent=config,
    guild_only=True,
)

infomaker = app_commands.Group(
    name="infomaker",
    description="Команды конфигурации для инфомейкеров.",
    parent=config,
    guild_only=True,
)

battlepass = app_commands.Group(
    name="battlepass",
    description="Команды конфигурации для боевого пропуска.",
    parent=config,
    guild_only=True,
)
