"""A Discord transformer utility for converting string command parameters to integers."""  # noqa: E501

import discord
from discord.app_commands import Transformer

from src.nightcore.exceptions import TransformStrToIntError


class StrToIntTransformer(Transformer):
    async def transform(
        self, interaction: discord.Interaction, value: str
    ) -> int:
        """Converts a string parameter to integer for Discord slash command."""

        try:
            res = int(value)
        except ValueError as e:
            raise TransformStrToIntError(
                "Ожидалось число в параметре с автокомплитом"
            ) from e

        return res
