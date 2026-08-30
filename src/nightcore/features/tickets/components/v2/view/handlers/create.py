"""Ticket create button handler."""

import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import CategoryChannel, Guild, Member
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models import (
    GuildLoggingConfig,
    GuildTicketsConfig,
    TicketState,
)
from src.infra.db.models.discord_webhook import DiscordWebhook
from src.infra.db.operations import (
    get_or_create_user,
    get_specified_guild_config,
    get_specified_webhook,
    get_user_ticket,
)
from src.nightcore.components.view.v2 import (
    ErrorViewV2,
    MissingPermissionsViewV2,
    SuccessViewV2,
)
from src.nightcore.features.tickets.events.dto import TicketChangeEventData
from src.nightcore.utils import ensure_messageable_channel_exists
from src.utils._enums import ChannelType, TicketStateEnum

logger = logging.getLogger(__name__)


async def handle_ticket_create_button(
    interaction: Interaction["Nightcore"],
) -> None:
    """Handle ticket:create button interaction."""

    from ..manage_ticket import ManageTicketViewV2

    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    user = cast(Member, interaction.user)

    await interaction.response.defer(thinking=True, ephemeral=True)

    if not guild.me.guild_permissions.manage_channels:
        await interaction.followup.send(
            view=MissingPermissionsViewV2(
                "У меня недостаточно прав для управления каналами.",
            ),
        )
        return

    outcome = ""
    current_tickets_count = 0
    new_tickets_category_id = 0
    create_ticket_ping_role_id = 0
    logging_webhook: DiscordWebhook | None = None
    new_channel_id = 0
    ticket_jump_url = ""

    async with bot.uow.start() as session:
        guild_config = await get_specified_guild_config(
            session,
            config_type=GuildTicketsConfig,
            guild_id=guild.id,
            for_update=True,
        )

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
            new_tickets_category_id = guild_config.new_tickets_category_id
            create_ticket_ping_role_id = (
                guild_config.create_ticket_ping_role_id
            )

            dbuser, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=user.id, for_update=True
            )

            if dbuser.ticket_ban:
                outcome = "user_ticket_banned"
            else:
                last_ticket = await get_user_ticket(
                    session,
                    guild_id=guild.id,
                    user_id=user.id,
                    for_update=True,
                )

                if last_ticket:
                    outcome = "user_has_open_ticket"
                else:
                    try:
                        current_tickets_count = guild_config.tickets_count + 1

                        guild_config.tickets_count = current_tickets_count

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
            logging_webhook = await get_specified_webhook(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_TICKETS,
            )

    if outcome == "ticket_system_not_configured":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Система тикетов не настроена",
                "Система тикетов не настроена на этом сервере.",
            ),
        )
        return

    if outcome == "user_ticket_banned":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Вы забанены",
                "Вам запрещено создавать тикеты.",
            ),
        )
        return

    if outcome == "user_has_open_ticket":
        await interaction.followup.send(
            view=ErrorViewV2(
                "У вас уже есть открытый тикет",
                "У вас уже есть открытый тикет. "
                "Пожалуйста, закройте его перед созданием нового.",
            ),
        )
        return

    if outcome == "ticket_creation_failed":
        await interaction.followup.send(
            view=ErrorViewV2(
                "Ошибка создания тикета",
                "Не удалось создать тикет. Пожалуйста, попробуйте позже.",
            ),
        )
        return

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
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Категория не найдена",
                    "Система тикетов настроена неправильно.",
                ),
            )
            return

        try:
            overwrites = new_tickets_category.overwrites
            overwrites[user] = discord.PermissionOverwrite(
                view_channel=True,
            )

            channel = await guild.create_text_channel(
                name=f"ticket-{current_tickets_count}",
                category=new_tickets_category,
                overwrites=overwrites,
            )

            new_channel_id = channel.id

            message = await channel.send(
                view=ManageTicketViewV2(
                    bot,
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
            await interaction.followup.send(
                view=ErrorViewV2(
                    "Ошибка создания канала",
                    "Не удалось создать канал тикета.",
                ),
            )
            return

        async with bot.uow.start() as session:
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

        if logging_webhook:
            bot.dispatch(
                "ticket_changed",
                data=TicketChangeEventData(
                    guild,
                    new_channel_id,
                    user.id,
                    None,
                    TicketStateEnum.OPENED,
                    logging_webhook,
                ),
            )

        await interaction.followup.send(
            view=SuccessViewV2(
                "Тикет создан",
                f"Ваш тикет был создан: [Перейти к тикету]({ticket_jump_url})",
            ),
        )
