"""Error embeds for the Nightcore bot."""

import discord
from discord.embeds import Embed


class NoConfigFoundEmbed(Embed):
    def __init__(self):
        super().__init__(
            title="No Configuration Found",
            description="No config found for this guild, but it will be created now. Please run this command again.",  # noqa
            color=discord.Color.red(),
        )


class NoOptionsSuppliedEmbed(Embed):
    def __init__(self):
        super().__init__(
            title="No Options Supplied",
            description="No options were supplied for this command.",
            color=discord.Color.yellow(),
        )


class ValidationErrorEmbed(Embed):
    def __init__(self, msg: str):
        super().__init__(
            title="Validation Error occurred",
            description=msg,
            color=discord.Color.red(),
        )
