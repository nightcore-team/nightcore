"""Setup module for creating and configuring the Nightcore bot instance."""

from src.infra.db.uow import UnitOfWork
from src.nightcore.bot import Nightcore


def create_bot(uow: UnitOfWork) -> Nightcore:
    """Create and return an instance of the Nightcore bot."""

    cog_modules = [
        # meta
        "src.nightcore.features.meta.commands.ping",
        "src.nightcore.features.meta.commands.avatar",
        "src.nightcore.features.meta.commands.banner",
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
        "src.nightcore.features.moderation.commands.voteban",
        "src.nightcore.features.moderation.commands.mpmute",
        "src.nightcore.features.moderation.commands.unmpmute",
        "src.nightcore.features.moderation.commands.vmute",
        "src.nightcore.features.moderation.commands.unvmute",
        "src.nightcore.features.moderation.commands.getmoderstats",
        "src.nightcore.features.moderation.commands.ticketban",
        "src.nightcore.features.moderation.commands.unticketban",
        "src.nightcore.features.moderation.commands.rrban",
        "src.nightcore.features.moderation.commands.unrrban",
        # moderation events
        "src.nightcore.features.moderation.events.kick",
        "src.nightcore.features.moderation.events.roles_change",
        "src.nightcore.features.moderation.events.message_clear",
        "src.nightcore.features.moderation.events.setname",
        "src.nightcore.features.moderation.events.mute",
        "src.nightcore.features.moderation.events.ban",
        "src.nightcore.features.moderation.events.ticketban",
        "src.nightcore.features.moderation.events.rrban",
        # tickets commands
        "src.nightcore.features.tickets.commands.ticketmessage",
        # tickets events
        "src.nightcore.features.tickets.events.ticket",
        # role requests commands
        "src.nightcore.features.role_requests.commands.rrmessage",
        # role requests events
        "src.nightcore.features.role_requests.events.stats",
        # proposal events
        "src.nightcore.features.proposals.events.proposal",
        # === global events
        "src.nightcore.events.reaction",
        "src.nightcore.events.message",
        "src.nightcore.events.error",
        # channels
        "src.nightcore.events.channel.create",
        "src.nightcore.events.channel.delete",
        "src.nightcore.events.channel.update",
        # tasks
        # "src.nightcore.tasks.unpunish",
        # "src.nightcore.tasks.delete_ticket",
        # "src.nightcore.tasks.delete_role_request",
    ]

    return Nightcore(
        cog_modules=cog_modules,
        uow=uow,
    )
