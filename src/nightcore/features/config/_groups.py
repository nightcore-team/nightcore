"""Groups for the configuration commands."""

from discord import app_commands

config = app_commands.Group(
    name="config",
    description="Команды конфигурации для бота Nightcore.",
)
other = app_commands.Group(
    name="other",
    description="Команды конфигурации для других настроек.",
    parent=config,
)
logging = app_commands.Group(
    name="logging",
    description="Команды конфигурации для логирования.",
    parent=config,
)
moderation = app_commands.Group(
    name="moderation",
    description="Команды конфигурации для модерации.",
    parent=config,
)

economy = app_commands.Group(
    name="economy",
    description="Команды конфигурации для экономики.",
    parent=config,
)

levels = app_commands.Group(
    name="levels",
    description="Команды конфигурации для уровней.",
    parent=config,
)

clans = app_commands.Group(
    name="clans",
    description="Команды конфигурации для кланов.",
    parent=config,
)

infomaker = app_commands.Group(
    name="infomaker",
    description="Команды конфигурации для инфомейкеров.",
    parent=config,
)

battlepass = app_commands.Group(
    name="battlepass",
    description="Команды конфигурации для боевого пропуска.",
    parent=config,
)
