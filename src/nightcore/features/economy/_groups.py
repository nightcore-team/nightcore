from discord import app_commands

give = app_commands.Group(
    name="give", description="Команды связанные с выдачей предметов/валюты."
)

case = app_commands.Group(
    name="case", description="Команды связанные с кейсами."
)

casino = app_commands.Group(
    name="casino", description="Команды связанные с казино."
)

temp = app_commands.Group(
    name="temp",
    description="Команды связанные с временной валютой или предметами.",
)
