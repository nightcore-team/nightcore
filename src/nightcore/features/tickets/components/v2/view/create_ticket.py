"""View for paginating infractions."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self, cast

import discord
from discord import ButtonStyle, CategoryChannel, Guild, Member
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

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models import (
    GuildLoggingConfig,
    GuildTicketsConfig,
    TicketState,
)
from src.infra.db.models._enums import ChannelType, TicketStateEnum
from src.infra.db.operations import (
    get_latest_user_ticket,
    get_or_create_user,
    get_specified_channel,
    get_specified_guild_config,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.tickets.events.dto import TicketChangeEventData
from src.nightcore.utils import discord_ts, ensure_messageable_channel_exists

from .manage_ticket import ManageTicketViewV2

logger = logging.getLogger(__name__)


class CreateTicketButton(ActionRow["CreateTicketViewV2"]):
    def __init__(self):
        super().__init__()

    @button(
        style=ButtonStyle.grey,
        label="Создать тикет",
        emoji="<:29909ticket:1442924723528007700>",
        custom_id="ticket:create",
    )
    async def create_ticket(
        self, interaction: Interaction, button: Button["CreateTicketViewV2"]
    ):
        """Button to create a ticket."""
        view = cast("CreateTicketViewV2", self.view)
        guild = cast(Guild, interaction.guild)
        user = cast(Member, interaction.user)

        await interaction.response.defer(thinking=True, ephemeral=True)

        if not guild.me.guild_permissions.manage_channels:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    view.bot.user.display_name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                    "У меня недостаточно прав для управления каналами.",
                ),
            )

        outcome = ""
        current_tickets_count = 0
        new_tickets_category_id = 0
        create_ticket_ping_role_id = 0
        logging_channel_id: int | None = None
        new_channel_id = 0
        ticket_jump_url = ""

        async with view.bot.uow.start() as session:
            guild_config = await get_specified_guild_config(
                session,
                config_type=GuildTicketsConfig,
                guild_id=guild.id,
            )

            if guild_config is None:
                logger.error(
                    "Failed to find ticket guild config in guild %s",
                    guild.id,
                )
                outcome = "ticket_system_not_configured"
            else:
                if not all(
                    [
                        guild_config.create_ticket_ping_role_id,
                        guild_config.new_tickets_category_id,
                        guild_config.pinned_tickets_category_id,
                        guild_config.closed_tickets_category_id,
                    ]
                ):
                    logger.error(
                        "Not all ticket categories are configured in guild %s",
                        guild.id,
                    )
                    outcome = "ticket_system_not_configured"
                else:
                    new_tickets_category_id = (
                        guild_config.new_tickets_category_id
                    )
                    create_ticket_ping_role_id = (
                        guild_config.create_ticket_ping_role_id
                    )

                    dbuser, _ = await get_or_create_user(
                        session, guild_id=guild.id, user_id=user.id
                    )

                    if dbuser.ticket_ban:
                        outcome = "user_ticket_banned"
                    else:
                        last_ticket = await get_latest_user_ticket(
                            session, guild_id=guild.id, user_id=user.id
                        )

                        if last_ticket and last_ticket.state not in [
                            TicketStateEnum.CLOSED,
                            TicketStateEnum.DELETED,
                        ]:
                            outcome = "user_has_open_ticket"
                        else:
                            try:
                                current_tickets_count = (
                                    guild_config.tickets_count + 1
                                )

                                guild_config.tickets_count = (
                                    current_tickets_count
                                )

                                outcome = "ready_to_create"

                            except Exception as e:
                                logger.error(
                                    "Failed to prepare ticket in guild %s, user %s: %s",  # noqa: E501
                                    guild.id,
                                    user.id,
                                    e,
                                )
                                outcome = "ticket_creation_failed"

            if outcome == "ready_to_create":
                logging_channel_id = await get_specified_channel(
                    session,
                    guild_id=guild.id,
                    config_type=GuildLoggingConfig,
                    channel_type=ChannelType.LOGGING_TICKETS,
                )

        if outcome == "ticket_system_not_configured":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Система тикетов не настроена",
                    "Система тикетов не настроена на этом сервере.",
                    view.bot.user.display_name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
            )

        if outcome == "user_ticket_banned":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Вы забанены",
                    "Вам запрещено создавать тикеты.",
                    view.bot.user.display_name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
            )

        if outcome == "user_has_open_ticket":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "У вас уже есть открытый тикет",
                    "У вас уже есть открытый тикет. Пожалуйста, закройте его перед созданием нового.",  # noqa: E501
                    view.bot.user.display_name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
            )

        if outcome == "ticket_creation_failed":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка создания тикета",
                    "Не удалось создать тикет. Пожалуйста, попробуйте позже.",
                    view.bot.user.display_name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
            )

        if outcome == "ready_to_create":
            new_tickets_category = cast(
                CategoryChannel,
                await ensure_messageable_channel_exists(
                    guild,
                    cast(int, new_tickets_category_id),
                ),
            )

            if not new_tickets_category:
                logger.error(
                    "Failed to find new tickets category in guild %s",
                    guild.id,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Категория не найдена",
                        "Система тикетов настроена неправильно.",
                        view.bot.user.display_name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            try:
                overwrites = new_tickets_category.overwrites
                overwrites[user] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    attach_files=True,
                    read_message_history=True,
                )

                channel = await guild.create_text_channel(
                    name=f"ticket-{current_tickets_count}",
                    category=new_tickets_category,
                    overwrites=overwrites,
                )

                new_channel_id = channel.id

                message = await channel.send(
                    view=ManageTicketViewV2(
                        view.bot,
                        ping_role_id=create_ticket_ping_role_id,
                        interaction_user_id=interaction.user.id,
                    ),
                )

                ticket_jump_url = message.jump_url

            except Exception as e:
                logger.error(
                    "Failed to create ticket channel in guild %s, category: %s, %s",  # noqa: E501
                    guild.id,
                    new_tickets_category.id,
                    e,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка создания канала",
                        "Не удалось создать канал тикета.",
                        view.bot.user.display_name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            async with view.bot.uow.start() as session:
                ticket_state = TicketState(
                    guild_id=guild.id,
                    author_id=user.id,
                    channel_id=new_channel_id,
                    state=TicketStateEnum.OPENED,
                )
                session.add(ticket_state)

                logger.info(
                    "[Ticket] Created ticket #%s for user %s in guild %s (channel: %s)",  # noqa: E501
                    current_tickets_count,
                    user.id,
                    guild.id,
                    new_channel_id,
                )

            if logging_channel_id:
                view.bot.dispatch(
                    "ticket_changed",
                    data=TicketChangeEventData(
                        guild,
                        new_channel_id,
                        user.id,
                        None,
                        TicketStateEnum.OPENED,
                        logging_channel_id,
                    ),
                )

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Тикет создан",
                    f"Ваш тикет был создан: [Перейти к тикету]({ticket_jump_url})",  # noqa: E501
                    view.bot.user.display_name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
            )


class CreateTicketViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
    ):
        """Create the layout view component."""
        super().__init__(timeout=None)
        self.bot = bot

        # important: clear previous items to avoid duplicate custom_id
        self.clear_items()

        container = Container[Self]()

        # Header
        container.add_item(TextDisplay[Self]("## Задайте ваш вопрос"))
        container.add_item(Separator[Self]())

        # main text
        container.add_item(
            TextDisplay[Self](
                "Здесь вы можете задать вопрос агентам поддержки относительно...\n...правил или поведения на Discord сервере"  # noqa: E501
            )
        )

        # action row
        container.add_item(Separator[Self]())
        container.add_item(CreateTicketButton())
        container.add_item(Separator[Self]())

        # Footer
        now = datetime.now(UTC)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)

    async def on_timeout(self):
        """Disable all buttons when the view times out."""

        def walk(item: Item[Self]):  # type: ignore
            if hasattr(item, "children"):
                for c in item.children:  # type: ignore
                    yield from walk(c)  # type: ignore
            yield item

        for comp in walk(self):  # type: ignore
            if isinstance(comp, Button):
                comp.disabled = True
