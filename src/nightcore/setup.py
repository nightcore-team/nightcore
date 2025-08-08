"""Setup module for creating and configuring the Nightcore bot instance."""

from src.infra.db.uow import UnitOfWork
from src.nightcore.bot import Nightcore


async def create_bot(uow: UnitOfWork) -> Nightcore:
    """Create and return an instance of the Nightcore bot."""

    cog_modules = [
        "src.nightcore.commands.ping",
        "src.nightcore.commands.avatar",
        "src.nightcore.commands.config",
    ]

    return Nightcore(
        cog_modules=cog_modules,
        uow=uow,
    )
