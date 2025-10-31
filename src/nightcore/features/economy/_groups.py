from discord import app_commands

give = app_commands.Group(
    name="give", description="Commands related to giving currency or items."
)

case = app_commands.Group(
    name="case", description="Commands related to cases."
)

casino = app_commands.Group(
    name="casino", description="Commands related to casino games."
)
