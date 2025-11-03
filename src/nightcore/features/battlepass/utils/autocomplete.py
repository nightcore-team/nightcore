"""Autocomplete utilities for battlepass levels."""

# from typing import TYPE_CHECKING, cast

# from discord import Guild, app_commands
# from discord.interactions import Interaction

# from src.infra.db.models import GuildEconomyConfig
# from src.nightcore.services.config import specified_guild_config

# if TYPE_CHECKING:
#     from src.nightcore.bot import Nightcore


# async def battlepass_levels_autocomplete(
#     interaction: Interaction["Nightcore"],
#     current: str,
# ) -> list[app_commands.Choice[str]]:
#     """Autocomplete for battlepass levels."""

#     bot = interaction.client
#     guild = cast(Guild, interaction.guild)

#     async with specified_guild_config(bot, guild.id, GuildEconomyConfig) as (
#         guild_config,
#         _,
#     ):
#         battlepass_rewards = guild_config.battlepass_rewards or []

#     result: list[app_commands.Choice[str]] = []
#     for level in battlepass_rewards:
#         result.append(
#             app_commands.Choice(
#                 name=f"Level {level['level']}",
#                 value=str(level["level"]),
#             )
#         )

#     return result
