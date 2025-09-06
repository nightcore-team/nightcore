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
        "src.nightcore.features.meta.commands.about",
        # config commands
        "src.nightcore.features.config",  # dir
        # moderation commands
        "src.nightcore.features.moderation.commands.kick",
        "src.nightcore.features.moderation.commands.fraction_role",
        "src.nightcore.features.moderation.commands.infractions",
        "src.nightcore.features.moderation.commands.setname",
        "src.nightcore.features.moderation.commands.clear",
        "src.nightcore.features.moderation.commands.rr",
        "src.nightcore.features.moderation.commands.mute",
        "src.nightcore.features.moderation.commands.unmute",
        "src.nightcore.features.moderation.commands.ban",
        "src.nightcore.features.moderation.commands.unban",
        "src.nightcore.features.moderation.commands.mpmute",
        "src.nightcore.features.moderation.commands.unmpmute",
        "src.nightcore.features.moderation.commands.vmute",
        "src.nightcore.features.moderation.commands.unvmute",
        # moderation events
        "src.nightcore.features.moderation.events.kick",
        "src.nightcore.features.moderation.events.roles_change",
        "src.nightcore.features.moderation.events.message_clear",
        "src.nightcore.features.moderation.events.setname",
        "src.nightcore.features.moderation.events.mute",
        "src.nightcore.features.moderation.events.ban",
        # global events
        "src.nightcore.events.reaction",
        "src.nightcore.events.message",
        "src.nightcore.events.error",
        "src.nightcore.events.member.update",
        # tasks
        "src.nightcore.tasks.unpunish",
    ]

    return Nightcore(
        cog_modules=cog_modules,
        uow=uow,
    )
