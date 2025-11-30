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
        "src.nightcore.features.meta.commands.rules",
        "src.nightcore.features.meta.commands.rolemembers",
        "src.nightcore.features.meta.commands.bugreport",
        # faq commands
        "src.nightcore.features.faq",
        # config commands
        "src.nightcore.features.config",
        # moderation commands
        "src.nightcore.features.moderation.commands.changestat",
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
        "src.nightcore.features.moderation.commands.notify",
        # moderation events
        "src.nightcore.features.moderation.events.kick",
        "src.nightcore.features.moderation.events.roles_change",
        "src.nightcore.features.moderation.events.message_clear",
        "src.nightcore.features.moderation.events.setname",
        "src.nightcore.features.moderation.events.mute",
        "src.nightcore.features.moderation.events.ban",
        "src.nightcore.features.moderation.events.ticketban",
        "src.nightcore.features.moderation.events.rrban",
        "src.nightcore.features.moderation.events.count_message",
        # === clans
        "src.nightcore.features.clans",
        # === clans events
        "src.nightcore.features.clans.events.order_notify",
        "src.nightcore.features.clans.events.count_clan_message",
        # === economy
        "src.nightcore.features.economy",
        "src.nightcore.features.economy.commands.top",
        "src.nightcore.features.economy.commands.pay",
        "src.nightcore.features.economy.commands.balance",
        "src.nightcore.features.economy.commands.shopmessage",
        "src.nightcore.features.economy.commands.reward",
        "src.nightcore.features.economy.commands.profile",
        "src.nightcore.features.economy.commands.paint",
        "src.nightcore.features.economy.events.award_notify",
        "src.nightcore.features.economy.events.transfer_notify",
        "src.nightcore.features.economy.events.order_notify",
        "src.nightcore.features.economy.events.count_message",
        "src.nightcore.features.economy.events.count_voice_activity",
        # === battlepass
        "src.nightcore.features.battlepass.commands.battlepass",
        # === tickets
        "src.nightcore.features.tickets.commands.ticketmessage",
        "src.nightcore.features.tickets.events.ticket",
        # === role requests
        "src.nightcore.features.role_requests.commands.rrmessage",
        # === proposals
        "src.nightcore.features.proposals.events.proposal",
        # === global events
        "src.nightcore.events.reaction.add",
        "src.nightcore.events.message.on",
        "src.nightcore.events.message.delete",
        "src.nightcore.events.message.update",
        "src.nightcore.events.error",
        "src.nightcore.events.interaction",
        "src.nightcore.events.channel.create",
        "src.nightcore.events.channel.delete",
        "src.nightcore.events.channel.update",
        "src.nightcore.events.member.add",
        "src.nightcore.events.member.leave",
        "src.nightcore.events.member.ban",
        "src.nightcore.events.member.update.gateway",
        "src.nightcore.events.member.update.default",
        "src.nightcore.events.member.update.infomaker",
        "src.nightcore.events.voice.gateway",
        "src.nightcore.events.voice.join",
        "src.nightcore.events.voice.leave",
        "src.nightcore.events.voice.switch",
        "src.nightcore.events.role.create",
        "src.nightcore.events.role.delete",
        "src.nightcore.events.role.update",
        # === private rooms
        "src.nightcore.features.private_rooms.events.create",
        "src.nightcore.features.private_rooms.events.delete",
        # === tasks
        # "src.nightcore.tasks.unpunish",
        # "src.nightcore.tasks.delete_ticket",
        # "src.nightcore.tasks.delete_role_request",
        # "src.nightcore.tasks.expired_notify",
        # "src.nightcore.tasks.check_forum",
        # "src.nightcore.tasks.clan_reputation",
        # "src.nightcore.tasks.temp_role",
        # "src.nightcore.tasks.temp_multiplier",
    ]

    return Nightcore(
        cog_modules=cog_modules,
        uow=uow,
    )
