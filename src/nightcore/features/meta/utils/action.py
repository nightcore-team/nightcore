"""This module provides utility functions for handling user actions."""

import random

import discord
from discord import app_commands

from . import gifs

DUO_ACTIONS = {"kiss", "bite", "hug", "slap"}

ACTION_CHOICES = [
    app_commands.Choice(name="Обнять", value="hug"),
    app_commands.Choice(name="Ударить", value="slap"),
    app_commands.Choice(name="Укусить", value="bite"),
    app_commands.Choice(name="Спать", value="sleep"),
    app_commands.Choice(name="Плакать", value="cry"),
    app_commands.Choice(name="Радоваться", value="happy"),
    app_commands.Choice(name="Грустить", value="sad"),
    app_commands.Choice(name="Курить", value="smoke"),
    app_commands.Choice(name="Поцеловать", value="kiss"),
]


def random_gif(gifs: list[str]) -> str:
    """Return a random GIF from the provided list."""
    return random.choice(gifs)


def build_action_embed(
    action: str,
    actor: discord.User | discord.Member,
    target: discord.User | discord.Member | None,
) -> discord.Embed:
    """Build an embed for the specified action."""
    color_map = {
        "hug": 0x9B59B6,  # Purple
        "slap": 0xE67E22,  # Orange
        "kiss": 0xFF66A5,  # Pink-ish
        "bite": 0x992D22,  # DarkRed
        "sleep": 0x95A5A6,  # Grey
        "smoke": 0x607D8B,  # DarkGrey/Blue
        "happy": 0xF1C40F,  # Gold
        "cry": 0x3498DB,  # Blue
        "sad": 0x2C3E50,  # DarkBlue
    }
    embed = discord.Embed(color=color_map.get(action, 0x2F3136))

    actor_mention = actor.mention
    target_mention = target.mention if target else None

    if action == "hug":
        embed.description = f"🫂 {actor_mention} обнял {target_mention} 🤗"
        embed.set_image(url=random_gif(gifs.HUG_GIFS))
    elif action == "slap":
        embed.description = f"👋 {actor_mention} ударил {target_mention} 😵"
        embed.set_image(url=random_gif(gifs.SLAP_GIFS))
    elif action == "kiss":
        embed.description = f"💋 {actor_mention} поцеловал {target_mention} 😘"
        embed.set_image(url=random_gif(gifs.KISS_GIFS))
    elif action == "bite":
        embed.description = f"{actor_mention} укусил {target_mention} 😖"
        embed.set_image(url=random_gif(gifs.BITE_GIFS))
    elif action == "sleep":
        embed.description = f"😴 {actor_mention} спит..."
        embed.set_image(url=random_gif(gifs.SLEEP_GIFS))
    elif action == "smoke":
        embed.description = f"🚬 {actor_mention} курит..."
        embed.set_image(url=random_gif(gifs.SMOKE_GIFS))
    elif action == "happy":
        embed.description = f"😊 {actor_mention} радуется!"
        embed.set_image(url=random_gif(gifs.HAPPY_GIFS))
    elif action == "cry":
        embed.description = f"😭 {actor_mention} плачет.."
        embed.set_image(url=random_gif(gifs.CRY_GIFS))
    elif action == "sad":
        embed.description = f"😢 {actor_mention} грустит..."
        embed.set_image(url=random_gif(gifs.SAD_GIFS))
    else:
        embed.description = f"{actor_mention} делает что-то странное..."

    return embed
