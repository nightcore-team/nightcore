"""A Discord transformer utility for converting string command parameters to integers."""  # noqa: E501

import discord
from discord.app_commands import Transformer

from src.nightcore.exceptions import TransformStrToIntError


class StrToIntTransformer(Transformer):
    async def transform(
        self, interaction: discord.Interaction, value: str
    ) -> int:
        """Converts a string parameter to integer for Discord slash command."""

        param_name = ""

        if interaction.data is not None:
            for option in interaction.data.get("options", []):
                if option["value"] == value:  # type: ignore
                    param_name = option["name"]

        try:
            res = int(value)
        except ValueError as e:
            raise TransformStrToIntError(
                f"Ожидался тип int в параметре {param_name}"
            ) from e

        return res
