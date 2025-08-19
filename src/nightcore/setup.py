"""Setup module for creating and configuring the Nightcore bot instance."""

from src.infra.db.uow import UnitOfWork
from src.nightcore.bot import Nightcore


def create_bot(uow: UnitOfWork) -> Nightcore:
    """Create and return an instance of the Nightcore bot."""

    cog_modules = [
        "src.nightcore.features.meta.commands.ping",
        "src.nightcore.features.meta.commands.avatar",
        "src.nightcore.features.config",  # dir
        "src.nightcore.events.reaction",
        "src.nightcore.events.message",
        "src.nightcore.events.error",
    ]

    return Nightcore(
        cog_modules=cog_modules,
        uow=uow,
    )
