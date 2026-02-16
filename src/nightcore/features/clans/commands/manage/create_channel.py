"""Create clan channel command."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, PermissionOverwrite, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildClansConfig
from src.infra.db.models._enums import ChannelType, ClanManageActionEnum
from src.infra.db.models.guild import GuildLoggingConfig
from src.infra.db.operations import (
    get_clan_by_id,
    get_specified_channel,
    get_specified_field,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.clans._groups import manage as manage_clan_group
from src.nightcore.features.clans.events.dto.clan_manage_notify import (
    ClanManageAction,
    ClanManageNotifyDTO,
)
from src.nightcore.features.clans.utils import clans_autocomplete
from src.nightcore.utils.object import (
    ensure_category_exists,
    ensure_role_exists,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@manage_clan_group.command(  # type: ignore
    name="create_channel", description="Создать текстовый канал для клана."
)
@app_commands.describe(
    clan="Клан, для которого нужно создать канал.",
)
@app_commands.autocomplete(clan=clans_autocomplete)
@check_required_permissions(PermissionsFlagEnum.CLANS_ACCESS)
async def create_channel(interaction: Interaction["Nightcore"], clan: str):
    """Create a text channel for an existing clan."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    try:
        clan_id = int(clan)
    except ValueError:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка получения информации о клане",
                "Не удалось найти данный клан в базе данных.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    await interaction.response.defer(ephemeral=True, thinking=True)

    # Check permissions
    if not guild.me.guild_permissions.manage_channels:
        return await interaction.followup.send(
            embed=MissingPermissionsEmbed(
                bot.user.name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
                "У меня нет прав на управление каналами в этом сервере.",
            ),
        )

    # Get clan from database
    outcome = ""
    clan_name = ""
    clan_role_id = 0
    create_clan_channel_category_id = None
    clans_logging_channel = None

    async with bot.uow.start() as session:
        dbclan = await get_clan_by_id(
            session, guild_id=guild.id, clan_id=clan_id
        )

        if not dbclan:
            outcome = "clan_not_found"

        else:
            clan_name = dbclan.name
            clan_role_id = dbclan.role_id

            # Get category for clan channels
            create_clan_channel_category_id = await get_specified_field(
                session,
                guild_id=guild.id,
                config_type=GuildClansConfig,
                field_name="create_clan_channel_category_id",
            )

            # Get logging channel
            clans_logging_channel = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_CLANS,
            )

    if outcome == "clan_not_found":
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка получения информации о клане",
                "Не удалось найти данный клан в базе данных.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    # Check if category is configured
    if not create_clan_channel_category_id:
        raise FieldNotConfiguredError("категория кланов")

    # Ensure clan role exists
    clan_role = await ensure_role_exists(guild, clan_role_id)
    if clan_role is None:
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка создания канала клана",
                f"Роль клана **{clan_name}** не найдена на сервере.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
        )

    # Ensure category exists
    category = await ensure_category_exists(
        guild, create_clan_channel_category_id
    )
    if category is None:
        logger.error(
            "[clans] Error fetching create clan channel category for "
            "guild %s: category not found",
            guild.id,
        )
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка создания канала клана",
                "Не удалось найти категорию для создания каналов кланов.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
        )

    # Create the clan channel
    try:
        channel = await guild.create_text_channel(
            name=f"{clan_name}-clan",
            category=category,
            overwrites={
                clan_role: PermissionOverwrite(
                    read_message_history=True,
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    add_reactions=True,
                )
            },
            reason=f"Создание канала для клана {clan_name}",
        )

        async with bot.uow.start() as session:
            dbclan = await session.merge(dbclan)

            if not dbclan:
                logger.error(
                    "[clans/create_channel] Clan %s not found in database "
                    "during channel creation in guild %s",
                    clan_id,
                    guild.id,
                )
                outcome = "clan_not_found_on_update"
            else:
                dbclan.clan_channel_id = channel.id

        if outcome == "clan_not_found_on_update":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка обновления информации о клане",
                    "Клан не найден в базе данных при обновлении информации о канале.",  # noqa: E501
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        logger.info(
            "[clans/create_channel] Created channel %s for clan %s in "
            "guild %s by user %s",
            channel.id,
            clan_name,
            guild.id,
            interaction.user.id,
        )

        # Dispatch notification event
        clan_channel_create_action = ClanManageAction(
            type=ClanManageActionEnum.CREATE,
            after=f"Создан канал {channel.mention}",
        )

        dto = ClanManageNotifyDTO(
            guild=guild,
            event_type="clan_manage_notify",
            actor_id=interaction.user.id,
            clan_name=clan_name,
            actions=[clan_channel_create_action],
            logging_channel_id=clans_logging_channel,
        )

        bot.dispatch("clan_manage_notify", dto)

        # Send success message
        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "Канал клана создан",
                f"Для клана **{clan_name}** был создан текстовый канал {channel.mention} в категории {category.mention}.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
        )

    except Exception as e:
        logger.error(
            "[clans/create_channel] Error creating clan channel in "
            "guild %s: %s",
            guild.id,
            e,
        )
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка создания канала клана",
                "Произошла ошибка при создании канала для клана.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
        )
