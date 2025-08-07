"""Setup module for initializing the Nightcore bot and its cogs."""

from discord.ext.commands import Cog

from src.infra.db.uow import UnitOfWork
from src.nightcore.bot import Nightcore
from src.nightcore.commands.avatar import Avatar
from src.nightcore.commands.config import Config
from src.nightcore.commands.ping import Ping


def available_cogs() -> list[Cog]:
    """Return a list of available cogs for the bot."""
    return [Ping, Avatar, Config]  # type: ignore


async def create_bot(uow: UnitOfWork) -> Nightcore:
    """Create and return an instance of the Nightcore bot."""
    bot = Nightcore(initial_cogs=available_cogs(), uow=uow)

    return bot
