"""View for managing tickets."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

import discord
from discord import ButtonStyle, CategoryChannel, Guild, Member, TextChannel
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models import GuildLoggingConfig, GuildTicketsConfig
from src.infra.db.models._enums import ChannelType, TicketStateEnum
from src.infra.db.operations import (
    get_head_moderation_access_roles,
    get_latest_user_ticket,
    get_moderation_access_roles,
    get_specified_channel,
)
from src.nightcore.components.embed import ErrorEmbed, MissingPermissionsEmbed
from src.nightcore.features.tickets.events.dto import TicketEventData
from src.nightcore.features.tickets.utils import extract_id_from_str
from src.nightcore.utils import (
    discord_ts,
    ensure_member_exists,
    ensure_messageable_channel_exists,
    has_any_role_from_sequence,
)

logger = logging.getLogger(__name__)


class TicketStateViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        state: TicketStateEnum,
        moderator_id: int,
        author_id: int,
    ) -> None:
        super().__init__(timeout=None)

        self.clear_items()

        container = Container[Self]()

        message: str = ""
        match state:
            case TicketStateEnum.OPENED:
                message = "### Тикет был открыт модератором {}"
            case TicketStateEnum.PINNED:
                message = "### Тикет был закреплен модератором {}"
            case TicketStateEnum.CLOSED:
                message = "### Тикет был закрыт модератором {}"
            case _:
                message = "Неизвестное состояние."

        container.add_item(
            TextDisplay[Self](message.format(f"<@{moderator_id}>"))
        )
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)} | <@{author_id}>"  # type: ignore  # noqa: E501
            )
        )
        self.add_item(container)


class ManageTicketButtons(ActionRow["ManageTicketViewV2"]):
    def __init__(self):
        super().__init__()

    @button(
        style=ButtonStyle.grey,
        label="Закрепить",
        emoji="📌",
        custom_id="ticket:pin",
    )  # type: ignore
    async def pin_ticket(
        self, interaction: Interaction, button: Button["ManageTicketViewV2"]
    ):
        """Pin the ticket."""
        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)
        user = cast(Member, interaction.user)

        # Extract interaction_user_id if not set
        if view.interaction_user_id is None:
            for component in interaction.message.components:  # type: ignore
                for child in component.children:  # type: ignore
                    if (
                        isinstance(child, discord.components.TextDisplay)
                        and child.id == 4
                    ):
                        view.interaction_user_id = extract_id_from_str(
                            child.content
                        )

                        break

        await interaction.response.defer()

        ticket_author = await ensure_member_exists(
            guild, cast(int, view.interaction_user_id)
        )
        if ticket_author is None:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось закрепить тикет",
                    "Автор тикета не найден на сервере. Вы можете закрыть тикет.",  # noqa: E501
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not guild.me.guild_permissions.manage_channels:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    "У меня нет прав на управление каналами.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        ticket_author_id = 0
        pinned_tickets_category_id = 0
        logging_channel_id: int | None = None

        async with view.bot.uow.start() as session:
            moderation_access_roles = await get_moderation_access_roles(
                session,
                guild_id=guild.id,
            )

            if not has_any_role_from_sequence(user, moderation_access_roles):
                outcome = "missing_permissions"
            else:
                ticket = await get_latest_user_ticket(
                    session,
                    guild_id=guild.id,
                    user_id=cast(int, view.interaction_user_id),
                )

                if ticket is None:
                    outcome = "ticket_not_found"
                elif ticket.state == TicketStateEnum.CLOSED:
                    outcome = "ticket_closed"
                elif ticket.state == TicketStateEnum.PINNED:
                    outcome = "already_pinned"
                else:
                    # Save ticket data
                    ticket_author_id = ticket.author_id

                    # Update ticket state to PINNED
                    ticket.moderator_id = user.id
                    ticket.state = TicketStateEnum.PINNED

                    # Get pinned tickets category ID
                    pinned_tickets_category_id = cast(
                        int,
                        await get_specified_channel(
                            session,
                            guild_id=guild.id,
                            config_type=GuildTicketsConfig,
                            channel_type=ChannelType.PINNED_TICKETS_CATEGORY,
                        ),
                    )

                    logging_channel_id = await get_specified_channel(
                        session,
                        guild_id=guild.id,
                        config_type=GuildLoggingConfig,
                        channel_type=ChannelType.LOGGING_TICKETS,
                    )

                    outcome = "success"

        if outcome == "missing_permissions":
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "ticket_not_found":
            logger.warning(
                "No ticket found for user %s in guild %s",
                view.interaction_user_id,
                guild.id,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось закрепить тикет",
                    "Тикет не найден для этого пользователя.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "ticket_closed":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось закрепить тикет",
                    "Вы не можете закрепить закрытый тикет.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "already_pinned":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось закрепить тикет",
                    "Этот тикет уже закреплен другим модератором.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            pinned_tickets_category = await ensure_messageable_channel_exists(
                guild=guild,
                channel_id=pinned_tickets_category_id,
            )

            if pinned_tickets_category is None:
                logger.error(
                    "Pinned tickets category %s not found in guild %s",
                    pinned_tickets_category_id,
                    guild.id,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Не удалось закрепить тикет",
                        "Категория закрепленных тикетов не найдена.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            await channel.edit(
                category=cast(CategoryChannel, pinned_tickets_category),
                overwrites=channel.overwrites,
            )

            await interaction.followup.send(
                view=TicketStateViewV2(
                    bot=view.bot,
                    state=TicketStateEnum.PINNED,
                    moderator_id=interaction.user.id,
                    author_id=ticket_author_id,
                ),
            )

            # Dispatch event
            if logging_channel_id:
                view.bot.dispatch(
                    "ticket_changed",
                    data=TicketEventData(
                        guild,
                        channel.id,
                        cast(int, view.interaction_user_id),
                        interaction.user.id,
                        TicketStateEnum.PINNED,
                        logging_channel_id,
                    ),
                )

            logger.info(
                "Ticket pinned by user %s in guild %s",
                interaction.user.id,
                guild.id,
            )

    @button(
        style=ButtonStyle.grey,
        label="Открыть",
        emoji="📂",
        custom_id="ticket:reopen",
    )
    async def reopen_ticket(
        self, interaction: Interaction, button: Button["ManageTicketViewV2"]
    ):
        """Reopen the ticket."""
        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)
        user = cast(Member, interaction.user)

        # Extract interaction_user_id if not set
        if view.interaction_user_id is None:
            for component in interaction.message.components:  # type: ignore
                for child in component.children:  # type: ignore
                    if (
                        isinstance(child, discord.components.TextDisplay)
                        and child.id == 4
                    ):
                        view.interaction_user_id = extract_id_from_str(
                            child.content
                        )
                        logger.info(
                            "Extracted interaction_user_id %s from message in guild %s",  # noqa: E501
                            view.interaction_user_id,
                            guild.id,
                        )
                        break

        await interaction.response.defer()

        ticket_author = await ensure_member_exists(
            guild, cast(int, view.interaction_user_id)
        )
        if ticket_author is None:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось открыть тикет",
                    "Автор тикета не найден на сервере.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if not guild.me.guild_permissions.manage_channels:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    "У меня нет прав на управление каналами.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        ticket_author_id = 0
        pinned_tickets_category_id = 0
        logging_channel_id: int | None = None

        async with view.bot.uow.start() as session:
            moderation_access_roles = await get_head_moderation_access_roles(
                session,
                guild_id=guild.id,
            )

            if not has_any_role_from_sequence(user, moderation_access_roles):
                outcome = "missing_permissions"
            else:
                ticket = await get_latest_user_ticket(
                    session,
                    guild_id=guild.id,
                    user_id=cast(int, view.interaction_user_id),
                )

                if ticket is None:
                    outcome = "ticket_not_found"
                elif ticket.state == TicketStateEnum.OPENED:
                    outcome = "already_opened"
                elif ticket.state == TicketStateEnum.PINNED:
                    outcome = "already_pinned"
                else:
                    # Save ticket data
                    ticket_author_id = ticket.author_id

                    # Update ticket state to OPENED (not PINNED)
                    ticket.moderator_id = user.id
                    ticket.state = TicketStateEnum.OPENED

                    # Get pinned tickets category ID (ticket will be moved here and reopened)  # noqa: E501
                    pinned_tickets_category_id = cast(
                        int,
                        await get_specified_channel(
                            session,
                            guild_id=guild.id,
                            config_type=GuildTicketsConfig,
                            channel_type=ChannelType.PINNED_TICKETS_CATEGORY,
                        ),
                    )

                    logging_channel_id = await get_specified_channel(
                        session,
                        guild_id=guild.id,
                        config_type=GuildLoggingConfig,
                        channel_type=ChannelType.LOGGING_TICKETS,
                    )

                    outcome = "success"

        if outcome == "missing_permissions":
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "ticket_not_found":
            logger.warning(
                "No ticket found for user %s in guild %s",
                view.interaction_user_id,
                guild.id,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось открыть тикет",
                    "Тикет не найден для этого пользователя.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "already_opened":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось открыть тикет",
                    "Вы не можете открыть уже открытый тикет. Просто закрепите его.",  # noqa: E501
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "already_pinned":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось открыть тикет",
                    "Этот тикет уже закреплен другим модератором.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            # Get pinned tickets category
            pinned_tickets_category = await ensure_messageable_channel_exists(
                guild=guild,
                channel_id=pinned_tickets_category_id,
            )

            if pinned_tickets_category is None:
                logger.error(
                    "Pinned tickets category %s not found in guild %s",
                    pinned_tickets_category_id,
                    guild.id,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Не удалось открыть тикет",
                        "Категория закрепленных тикетов настроена неправильно.",  # noqa: E501
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            # Update channel permissions to grant ticket author access
            overwrites = channel.overwrites
            overwrites[ticket_author] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True,
            )

            await channel.edit(
                category=cast(CategoryChannel, pinned_tickets_category),
                overwrites=overwrites,
            )

            await interaction.followup.send(
                view=TicketStateViewV2(
                    bot=view.bot,
                    state=TicketStateEnum.OPENED,
                    moderator_id=interaction.user.id,
                    author_id=ticket_author_id,
                ),
            )

            # Dispatch event with OPENED state
            if logging_channel_id:
                view.bot.dispatch(
                    "ticket_changed",
                    data=TicketEventData(
                        guild,
                        channel.id,
                        cast(int, view.interaction_user_id),
                        interaction.user.id,
                        TicketStateEnum.OPENED,
                        logging_channel_id,
                    ),
                )

            logger.info(
                "Ticket reopened by user %s in guild %s",
                interaction.user.id,
                guild.id,
            )

    @button(
        style=ButtonStyle.grey,
        label="Закрыть",
        emoji="🔒",
        custom_id="ticket:close",
    )
    async def close_ticket(
        self, interaction: Interaction, button: Button["ManageTicketViewV2"]
    ):
        """Close the ticket."""
        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)
        user = cast(Member, interaction.user)

        # Extract interaction_user_id if not set
        if view.interaction_user_id is None:
            for component in interaction.message.components:  # type: ignore
                for child in component.children:  # type: ignore
                    if (
                        isinstance(child, discord.components.TextDisplay)
                        and child.id == 4
                    ):
                        view.interaction_user_id = extract_id_from_str(
                            child.content
                        )
                        break

        await interaction.response.defer()

        ticket_author = await ensure_member_exists(
            guild, cast(int, view.interaction_user_id)
        )

        if not guild.me.guild_permissions.manage_channels:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    "У меня нет прав на управление каналами.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        outcome = ""
        ticket_author_id = 0
        closed_tickets_category_id = 0
        logging_channel_id: int | None = None

        async with view.bot.uow.start() as session:
            moderation_access_roles = await get_moderation_access_roles(
                session,
                guild_id=guild.id,
            )

            if not has_any_role_from_sequence(user, moderation_access_roles):
                outcome = "missing_permissions"
            else:
                ticket = await get_latest_user_ticket(
                    session,
                    guild_id=guild.id,
                    user_id=cast(int, view.interaction_user_id),
                )

                if ticket is None:
                    outcome = "ticket_not_found"
                elif ticket.state == TicketStateEnum.CLOSED:
                    outcome = "already_closed"
                else:
                    # Save ticket data
                    ticket_author_id = ticket.author_id

                    # Update ticket state to CLOSED
                    ticket.moderator_id = user.id
                    ticket.state = TicketStateEnum.CLOSED

                    # Get closed tickets category ID
                    closed_tickets_category_id = cast(
                        int,
                        await get_specified_channel(
                            session,
                            guild_id=guild.id,
                            config_type=GuildTicketsConfig,
                            channel_type=ChannelType.CLOSED_TICKETS_CATEGORY,
                        ),
                    )

                    logging_channel_id = await get_specified_channel(
                        session,
                        guild_id=guild.id,
                        config_type=GuildLoggingConfig,
                        channel_type=ChannelType.LOGGING_TICKETS,
                    )

                    outcome = "success"

        if outcome == "missing_permissions":
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "ticket_not_found":
            logger.warning(
                "No ticket found for user %s in guild %s",
                view.interaction_user_id,
                guild.id,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось закрыть тикет",
                    "Тикет не найден для этого пользователя.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "already_closed":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Не удалось закрыть тикет",
                    "Этот тикет уже закрыт.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            closed_tickets_category = await ensure_messageable_channel_exists(
                guild=guild,
                channel_id=closed_tickets_category_id,
            )

            if closed_tickets_category is None:
                logger.error(
                    "Closed tickets category %s not found in guild %s",
                    closed_tickets_category_id,
                    guild.id,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Не удалось закрыть тикет",
                        "Категория закрытых тикетов не найдена.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            overwrites = channel.overwrites
            if ticket_author is not None:
                overwrites[ticket_author] = discord.PermissionOverwrite(
                    read_messages=False,
                    send_messages=False,
                )
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                read_messages=False,
                send_messages=False,
            )

            await channel.edit(
                category=cast(CategoryChannel, closed_tickets_category),
                overwrites=overwrites,
            )

            await interaction.followup.send(
                view=TicketStateViewV2(
                    bot=view.bot,
                    state=TicketStateEnum.CLOSED,
                    moderator_id=interaction.user.id,
                    author_id=ticket_author_id,
                ),
            )

            # Dispatch event
            if logging_channel_id:
                view.bot.dispatch(
                    "ticket_changed",
                    data=TicketEventData(
                        guild,
                        channel.id,
                        cast(int, view.interaction_user_id),
                        interaction.user.id,
                        TicketStateEnum.CLOSED,
                        logging_channel_id,
                    ),
                )

            logger.info(
                "Ticket closed by user %s in guild %s",
                interaction.user.id,
                guild.id,
            )


class ManageTicketViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        ping_role_id: int | None = None,
        interaction_user_id: int | None = None,
    ):
        """Create the layout view component."""
        super().__init__(timeout=None)
        self.bot = bot
        self.ping_role_id = cast(int, ping_role_id)
        self.interaction_user_id = interaction_user_id

        self.clear_items()

        container = Container[Self]()

        # Main text
        container.add_item(
            TextDisplay[Self](
                f"### Уважаемый <@{interaction_user_id}>, \nесли у вас есть жалобы на работу модераторов, пожалуйста, обратитесь на [форум Arz Guard](https://forum.arzguard.com)."  # noqa: E501
            )
        )

        # Action row
        container.add_item(Separator[Self]())
        container.add_item(ManageTicketButtons())
        container.add_item(Separator[Self]())

        # Footer
        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)} | <@&{ping_role_id}>"  # type: ignore  # noqa: E501
            )
        )

        self.add_item(container)
