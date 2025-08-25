"""Setup module for creating and configuring the Nightcore bot instance."""

from src.infra.db.uow import UnitOfWork
from src.nightcore.bot import Nightcore


def create_bot(uow: UnitOfWork) -> Nightcore:
    """Create and return an instance of the Nightcore bot."""

    cog_modules = [
        # meta
        "src.nightcore.features.meta.commands.ping",
        "src.nightcore.features.meta.commands.avatar",
        "src.nightcore.features.meta.commands.action",
        # config commands
        "src.nightcore.features.config",  # dir
        # moderation commands
        "src.nightcore.features.moderation.commands.kick",
        "src.nightcore.features.moderation.commands.fraction_role",
        "src.nightcore.features.moderation.commands.infractions",
        "src.nightcore.features.moderation.commands.setname",
        "src.nightcore.features.moderation.events",
        # global events
        "src.nightcore.events.reaction",
        "src.nightcore.events.message",
        "src.nightcore.events.error",
    ]

    return Nightcore(
        cog_modules=cog_modules,
        uow=uow,
    )
