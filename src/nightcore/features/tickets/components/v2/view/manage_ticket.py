"""View for managing tickets."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self, cast

import discord
from discord import (
    ButtonStyle,
    CategoryChannel,
    Color,
    Guild,
    Member,
    TextChannel,
    app_commands,
)
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    Item,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

from src.nightcore.utils.lock_manager import AsyncioLockTypeEnum

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models import GuildLoggingConfig, GuildTicketsConfig
from src.infra.db.models.discord_webhook import DiscordWebhook
from src.infra.db.operations import (
    get_specified_channel,
    get_specified_webhook,
    get_ticket_state,
)
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    MissingPermissionsViewV2,
)
from src.nightcore.features.tickets.events.dto import TicketChangeEventData
from src.nightcore.utils import ensure_messageable_channel_exists
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.time_utils import discord_ts
from src.utils._enums import ChannelType, TicketStateEnum

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

        container = Container[Self](accent_color=Color.from_str("#5DADE2"))

        message: str = ""
        match state:
            case TicketStateEnum.OPENED:
                message = f"### <@{author_id}>, тикет был открыт модератором <@{moderator_id}>"  # noqa: E501
            case TicketStateEnum.PINNED:
                message = f"### <@{author_id}>, тикет был закреплен модератором <@{moderator_id}>"  # noqa: E501
            case TicketStateEnum.CLOSED:
                message = f"### <@{author_id}>, тикет был закрыт модератором <@{moderator_id}>"  # noqa: E501
            case _:
                message = "Неизвестное состояние."

        container.add_item(
            TextDisplay[Self](message.format(f"<@{moderator_id}>"))
        )

        self.add_item(container)


class ManageTicketButtons(ActionRow["ManageTicketViewV2"]):
    def __init__(self):
        super().__init__()

    @button(
        style=ButtonStyle.grey,
        label="Закрепить",
        emoji="<:nightcoreTicketPin:1540819251508682782>",
        custom_id="ticket:pin",
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def pin_ticket(
        self, interaction: Interaction, button: Button["ManageTicketViewV2"]
    ):
        """Pin the ticket."""

        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)
        user = cast(Member, interaction.user)

        await interaction.response.defer()

        if not guild.me.guild_permissions.manage_channels:
            await interaction.followup.send(
                view=MissingPermissionsViewV2(
                    "У меня нет прав на управление каналами.",
                ),
                ephemeral=True,
            )
            return

        outcome = ""
        ticket_author_id = 0
        pinned_tickets_category_id = 0
        logging_webhook: DiscordWebhook | None = None

        async with (
            view.bot.lock_manager.acquire(
                AsyncioLockTypeEnum.TicketManageAction, channel.id
            ),
            view.bot.uow.start() as session,
        ):
            ticket_state = await get_ticket_state(
                session, guild_id=guild.id, channel_id=channel.id
            )

            if ticket_state is None:
                outcome = "ticket_not_found"
            elif ticket_state.state == TicketStateEnum.CLOSED:
                outcome = "ticket_closed"
            elif ticket_state.state == TicketStateEnum.PINNED:
                outcome = "already_pinned"
            else:
                # Save ticket data
                ticket_author_id = ticket_state.author_id
                # Update ticket state to PINNED
                ticket_state.moderator_id = user.id
                ticket_state.state = TicketStateEnum.PINNED
                ticket_state.updated_at = datetime.now(UTC)

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

                logging_webhook = await get_specified_webhook(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_TICKETS,
                )

                outcome = "success"

        if outcome == "ticket_not_found":
            logger.warning(
                "No ticket found for user %s in guild %s",
                view.interaction_user_id,
                guild.id,
            )
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось закрепить тикет",
                    "Тикет не найден для этого пользователя.",
                ),
                ephemeral=True,
            )
            return

        if outcome == "ticket_closed":
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось закрепить тикет",
                    "Вы не можете закрепить закрытый тикет.",
                ),
                ephemeral=True,
            )
            return

        if outcome == "already_pinned":
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось закрепить тикет",
                    "Этот тикет уже закреплен.",
                ),
                ephemeral=True,
            )
            return

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
                await interaction.followup.send(
                    view=ErrorViewV2(
                        "Не удалось закрепить тикет",
                        "Категория закрепленных тикетов не найдена.",
                    ),
                    ephemeral=True,
                )
                return

            await channel.edit(
                category=cast(CategoryChannel, pinned_tickets_category),
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
            if logging_webhook:
                view.bot.dispatch(
                    "ticket_changed",
                    data=TicketChangeEventData(
                        guild,
                        channel.id,
                        ticket_author_id,
                        interaction.user.id,
                        TicketStateEnum.PINNED,
                        logging_webhook,
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
        emoji="<:nightcoreTicketOpen:1540818951586586754>",
        custom_id="ticket:reopen",
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.HEAD_MODERATION_ACCESS)  # type: ignore
    async def reopen_ticket(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["ManageTicketViewV2"],
    ):
        """Reopen the ticket."""

        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)

        await interaction.response.defer()

        if not guild.me.guild_permissions.manage_channels:
            await interaction.followup.send(
                view=MissingPermissionsViewV2(
                    "У меня нет прав на управление каналами.",
                ),
                ephemeral=True,
            )
            return

        outcome = ""
        ticket_author_id = 0
        pinned_tickets_category_id = 0
        logging_webhook: DiscordWebhook | None = None

        async with (
            view.bot.lock_manager.acquire(
                AsyncioLockTypeEnum.TicketManageAction, channel.id
            ),
            view.bot.uow.start() as session,
        ):
            ticket = await get_ticket_state(
                session,
                guild_id=guild.id,
                channel_id=channel.id,
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

                # Update ticket state to PINNED
                ticket.state = TicketStateEnum.PINNED
                ticket.updated_at = datetime.now(UTC)

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

                logging_webhook = await get_specified_webhook(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_TICKETS,
                )

                outcome = "success"

        if outcome == "ticket_not_found":
            logger.warning(
                "No ticket found for user %s in guild %s",
                ticket_author_id,
                guild.id,
            )
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось открыть тикет",
                    "Тикет не найден для этого пользователя.",
                ),
                ephemeral=True,
            )
            return

        if outcome == "already_opened":
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось открыть тикет",
                    "Вы не можете открыть уже открытый тикет. ",
                ),
                ephemeral=True,
            )
            return

        if outcome == "already_pinned":
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось открыть тикет",
                    "Этот тикет уже закреплен другим модератором.",
                ),
                ephemeral=True,
            )
            return

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
                await interaction.followup.send(
                    view=ErrorViewV2(
                        "Не удалось открыть тикет",
                        "Категория закрепленных тикетов "
                        "настроена неправильно.",
                    ),
                    ephemeral=True,
                )
                return

            overwrites = channel.overwrites

            overwrites[guild.default_role] = discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True,
                view_channel=False,
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
            if logging_webhook:
                view.bot.dispatch(
                    "ticket_changed",
                    data=TicketChangeEventData(
                        guild,
                        channel.id,
                        ticket_author_id,
                        interaction.user.id,
                        TicketStateEnum.OPENED,
                        logging_webhook,
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
        emoji="<:nightcoreTicketClose:1540819066694926456>",
        custom_id="ticket:close",
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.MODERATION_ACCESS)  # type: ignore
    async def close_ticket(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["ManageTicketViewV2"],
    ):
        """Close the ticket."""

        view = cast(ManageTicketViewV2, self.view)
        guild = cast(Guild, interaction.guild)
        channel = cast(TextChannel, interaction.channel)
        user = cast(Member, interaction.user)

        await interaction.response.defer()

        if not guild.me.guild_permissions.manage_channels:
            await interaction.followup.send(
                view=MissingPermissionsViewV2(
                    "У меня нет прав на управление каналами.",
                ),
                ephemeral=True,
            )
            return

        outcome = ""
        ticket_author_id = 0
        closed_tickets_category_id = 0
        logging_webhook: DiscordWebhook | None = None

        async with (
            view.bot.lock_manager.acquire(
                AsyncioLockTypeEnum.TicketManageAction, channel.id
            ),
            view.bot.uow.start() as session,
        ):
            ticket = await get_ticket_state(
                session,
                guild_id=guild.id,
                channel_id=channel.id,
            )

            if ticket is None:
                outcome = "ticket_not_found"
            elif ticket.state == TicketStateEnum.CLOSED:
                outcome = "already_closed"
            else:
                # Save ticket data
                ticket_author_id = ticket.author_id

                # Update ticket state to CLOSED
                ticket.state = TicketStateEnum.CLOSED
                ticket.updated_at = datetime.now(UTC)

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

                logging_webhook = await get_specified_webhook(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_TICKETS,
                )

                outcome = "success"

        if outcome == "ticket_not_found":
            logger.warning(
                "No ticket found for user %s in guild %s",
                view.interaction_user_id,
                guild.id,
            )
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось закрыть тикет",
                    "Тикет не найден для этого пользователя.",
                ),
                ephemeral=True,
            )
            return

        if outcome == "already_closed":
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Не удалось закрыть тикет",
                    "Этот тикет уже закрыт.",
                ),
                ephemeral=True,
            )
            return

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
                await interaction.followup.send(
                    view=ErrorViewV2(
                        "Не удалось закрыть тикет",
                        "Категория закрытых тикетов не найдена.",
                    ),
                    ephemeral=True,
                )
                return

            overwrites = channel.overwrites

            overwrites[guild.default_role] = discord.PermissionOverwrite(
                send_messages=False,
                view_channel=False,
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
            if logging_webhook:
                view.bot.dispatch(
                    "ticket_changed",
                    data=TicketChangeEventData(
                        guild,
                        channel.id,
                        ticket_author_id,
                        user.id,
                        TicketStateEnum.CLOSED,
                        logging_webhook,
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

        container = Container[Self](accent_color=Color.from_str("#5DADE2"))

        # Main text
        container.add_item(
            TextDisplay[Self](
                f"### <:nightcoreTicketNew:1540818406977052812> Обращение от пользователя <@{interaction_user_id}> \n> Если у вас есть жалобы на работу модераторов, пожалуйста, обратитесь на [форум Arz Guard](https://forum.arzguard.com)."  # noqa: E501
            )
        )

        # Action row
        container.add_item(Separator[Self]())
        container.add_item(ManageTicketButtons())
        container.add_item(Separator[Self]())

        # Footer
        now = datetime.now(UTC)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)} | <@&{ping_role_id}>"  # type: ignore  # noqa: E501
            )
        )

        self.add_item(container)

    async def on_error(
        self,
        interaction: Interaction,
        error: Exception,
        item: Item[Self],
    ):
        """Handle errors for button interactions."""
        original = getattr(error, "original", error)

        if not isinstance(original, app_commands.MissingPermissions):
            logger.error(
                "Unknown error in ticket manage component", exc_info=error
            )
            return

        missing_perms: list[str] = getattr(original, "missing_permissions", [])

        _missing_perms = ", ".join(missing_perms)

        if not interaction.response.is_done():
            await interaction.response.send_message(
                view=MissingPermissionsViewV2(
                    "Вам не хватает следующих прав для "
                    f"использования этой команды: {_missing_perms}.",
                ),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                view=MissingPermissionsViewV2(
                    "Вам не хватает следующих прав для "
                    f"использования этой команды: {missing_perms}.",
                ),
                ephemeral=True,
            )
