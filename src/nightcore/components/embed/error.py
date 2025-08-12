""""""

import discord
from discord.embeds import Embed


class NoConfigFoundEmbed(Embed):
    def __init__(self):
        super().__init__(
            title="No Configuration Found",
            description="No config found for this guild, but it will be created now. Please run this command again.",  # noqa
            color=discord.Color.red(),
        )
