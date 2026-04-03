from discord import app_commands

forum = app_commands.Group(
    name="forum",
    description="Команды связанные с конфигурацией форума.",
    guild_only=True,
)
