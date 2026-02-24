"""Clan creation command."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, PermissionOverwrite, app_commands
from discord.interactions import Interaction
from sqlalchemy.exc import IntegrityError

from src.config.config import config
from src.infra.db.models import GuildClansConfig
from src.infra.db.models._enums import (
    ChannelType,
    ClanManageActionEnum,
    ClanMemberRoleEnum,
)
from src.infra.db.models.guild import GuildLoggingConfig
from src.infra.db.operations import (
    create_clan,
    create_clan_member,
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
from src.nightcore.utils import safe_delete_role
from src.nightcore.utils.object import ensure_category_exists
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@manage_clan_group.command(name="create", description="Создать новый клан.")  # type: ignore
@app_commands.describe(
    name="Название клана.",
    leader="Пользователь, который станет лидером клана.",
    color="Цвет роли клана в HEX формате (например, #FF5733).",
    create_channel="Создавать ли текстовый канал для клана (требуется указать категорию для каналов кланов в настройках).",  # noqa: E501
)
@check_required_permissions(PermissionsFlagEnum.CLANS_ACCESS)
async def create(
    interaction: Interaction["Nightcore"],
    name: app_commands.Range[str, 1, 100],
    leader: Member,
    color: str,
    create_channel: bool = False,
):
    """Create a new clan."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        color_int = int(color.lstrip("#"), 16)
    except ValueError:
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка создания клана",
                "Неверный формат цвета. Пожалуйста, используйте HEX формат, например, #FF5733.",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
        )

    if not guild.me.guild_permissions.manage_roles:
        return await interaction.followup.send(
            embed=MissingPermissionsEmbed(
                bot.user.name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
                "У меня нет прав на управление ролями в этом сервере.",
            ),
        )

    if len(guild.roles) == config.bot.MAX_GUILD_ROLES_COUNT:
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка создания клана",
                "Достигнуто максимальное количество ролей в гильдии.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
        )

    try:
        clan_role = await guild.create_role(
            name=name,
            colour=discord.Colour(color_int),
            reason=f"Создание роли клана {name}",
        )
    except Exception as e:
        logger.error(
            "[clans] Error creating clan role in guild %s: %s", guild.id, e
        )
        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка создания роли клана",
                "Произошла ошибка при создании роли клана в сервере.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
        )

    # Wrap UoW in try-except to handle errors after transaction
    outcome = None
    error_msg = ""
    clan = None  # Initialize clan for later use

    try:
        async with bot.uow.start() as session:
            clan = await create_clan(
                session,
                guild_id=guild.id,
                name=name,
                role_id=clan_role.id,
            )
            await session.flush()

            await create_clan_member(
                session,
                guild_id=guild.id,
                clan_id=clan.id,
                user_id=leader.id,
                role=ClanMemberRoleEnum.LEADER,
            )

    except IntegrityError as e:
        outcome = "integrity_error"
        error_msg = str(e)

    except Exception as e:
        outcome = "general_error"
        logger.exception(
            "[clans] Error creating clan in database for guild %s: %s",
            guild.id,
            e,
        )

    # Handle errors after transaction is complete
    if outcome == "integrity_error":
        # Check if it's a clan name conflict or member already in clan
        if "uq_member_guild_user" in error_msg:
            user_message = (
                f"Пользователь {leader.mention} уже состоит в другом клане."  # noqa: E501
            )
        elif (
            "uq_clan_guild_name" in error_msg
            or "clan_name" in error_msg.lower()
        ):
            user_message = f"Клан с таким именем ({name}) уже существует."
        else:
            user_message = "Произошла ошибка при создании клана. Возможно, клан с таким именем уже существует или пользователь уже в другом клане."  # noqa: E501

        try:
            asyncio.create_task(
                safe_delete_role(
                    clan_role,
                    reason="Откат создания роли клана из-за ошибки в базе данных.",  # noqa: E501
                )
            )
        except Exception as delete_error:
            logger.error(
                "[clans] Error deleting clan role in guild %s during rollback: %s",  # noqa: E501
                guild.id,
                delete_error,
            )

        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка создания клана",
                user_message,
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
        )

    if outcome == "general_error":
        try:
            asyncio.create_task(
                safe_delete_role(
                    clan_role,
                    reason="Откат создания роли клана из-за ошибки в базе данных.",  # noqa: E501
                )
            )
        except Exception as delete_error:
            logger.error(
                "[clans] Error deleting clan role in guild %s during rollback: %s",  # noqa: E501
                guild.id,
                delete_error,
            )

        return await interaction.followup.send(
            embed=ErrorEmbed(
                "Ошибка создания клана",
                "Произошла ошибка при создании клана в базе данных.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
        )

    asyncio.create_task(
        leader.add_roles(clan_role, reason="Назначение роли лидера клана.")
    )

    logger.info(
        "[command] - invoked user=%s guild=%s clan_name=%s leader=%s color=%s",
        interaction.user.id,
        guild.id,
        name,
        leader.id,
        color_int,
    )

    async with bot.uow.start() as session:
        clans_logging_channel = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_CLANS,
        )
        if create_channel:
            create_clan_channel_category_id = await get_specified_field(
                session,
                guild_id=guild.id,
                config_type=GuildClansConfig,
                field_name="create_clan_channel_category_id",
            )

    clan_create_action = ClanManageAction(
        type=ClanManageActionEnum.CREATE,
    )

    dto = ClanManageNotifyDTO(
        guild=guild,
        event_type="clan_manage_notify",
        actor_id=interaction.user.id,
        clan_name=name,
        actions=[clan_create_action],
        logging_channel_id=clans_logging_channel,
    )

    bot.dispatch("clan_manage_notify", dto)

    await interaction.followup.send(
        embed=SuccessMoveEmbed(
            "Клан успешно создан",
            f"Клан **{name}** успешно создан, и роль назначена пользователю {leader.mention}.",  # noqa: E501
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    # Only proceed with channel creation if clan was successfully created
    if outcome is None and create_channel and clan is not None:
        if create_clan_channel_category_id:  # type: ignore
            category = await ensure_category_exists(
                guild, create_clan_channel_category_id
            )

            if category is None:
                logger.error(
                    "[clans] Error fetching create clan channel category for guild %s: category not found",  # noqa: E501
                    guild.id,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка создания канала клана",
                        "Не удалось найти категорию для создания каналов кланов. ",  # noqa: E501
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            try:
                channel = await guild.create_text_channel(
                    name=f"{name}-clan",
                    category=category,
                    overwrites={
                        guild.default_role: PermissionOverwrite(
                            read_message_history=False,
                            read_messages=False,
                        ),
                        clan_role: PermissionOverwrite(
                            read_message_history=True,
                            read_messages=True,
                            send_messages=True,
                            attach_files=True,
                            add_reactions=True,
                        ),
                    },
                )
                async with bot.uow.start() as session:
                    # clan is guaranteed to be not None here due to if check
                    assert clan is not None
                    merged_clan = await session.merge(clan)
                    merged_clan.clan_channel_id = channel.id

                await interaction.followup.send(
                    embed=SuccessMoveEmbed(
                        "Канал клана создан",
                        f"Для клана **{name}** был создан текстовый канал в категории {category.mention}.",  # noqa: E501
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
            except Exception as e:
                logger.error(
                    "[clans] Error creating clan channel in guild %s: %s",
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
                    ephemeral=True,
                )

        else:
            raise FieldNotConfiguredError("категория кланов")
