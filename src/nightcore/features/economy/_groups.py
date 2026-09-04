from discord import app_commands

give = app_commands.Group(
    name="give",
    description="Команды связанные с выдачей предметов/валюты.",
    guild_only=True,
)

remove = app_commands.Group(
    name="remove",
    description="Команды связанные с удалением предметов/валюты.",
    guild_only=True,
)

case = app_commands.Group(
    name="case",
    description="Команды связанные с кейсами.",
    guild_only=True,
)

color = app_commands.Group(
    name="color",
    description="Команды связанные с цветами.",
    guild_only=True,
)

rainbow = app_commands.Group(
    name="rainbow",
    description="Команды связанные с радужной ролью.",
    guild_only=True,
)

casino = app_commands.Group(
    name="casino",
    description="Команды связанные с казино.",
    guild_only=True,
)

temp = app_commands.Group(
    name="temp",
    description="Команды связанные с временной валютой или предметами.",
    guild_only=True,
)

bank = app_commands.Group(
    name="bank",
    description="Команды связанные с банковской системой.",
    guild_only=True,
)

extra = app_commands.Group(
    name="extra",
    description="Команды связанные с дополнительными счетами в банке.",
    guild_only=True,
    parent=bank,
)
