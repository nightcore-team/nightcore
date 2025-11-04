"""Clan creation command."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, app_commands
from discord.interactions import Interaction
from sqlalchemy.exc import IntegrityError

from src.infra.db.models import GuildClansConfig
from src.infra.db.models._enums import ClanMemberRoleEnum
from src.infra.db.operations import (
    create_clan,
    create_clan_member,
    get_specified_field,
)
from src.nightcore.components.embed import (
    EntityNotFoundEmbed,
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.clans._groups import manage as manage_clan_group
from src.nightcore.utils import (
    ensure_member_exists,
    has_any_role_from_sequence,
    safe_delete_role,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@manage_clan_group.command(name="create", description="Создать новый клан.")
@app_commands.describe(
    name="Название клана.",
    leader="Пользователь, который станет лидером клана.",
    color="Цвет роли клана в HEX формате (например, #FF5733).",
)
async def create(
    interaction: Interaction["Nightcore"],
    name: str,
    leader: discord.Member,
    color: str,
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

    member_task = asyncio.create_task(
        ensure_member_exists(guild, user_id=leader.id)
    )
    async with bot.uow.start() as session:
        clans_access_roles_task = asyncio.create_task(
            get_specified_field(
                session,
                guild_id=guild.id,
                config_type=GuildClansConfig,
                field_name="clans_access_roles_ids",
            )
        )

        member, clans_access_roles_ids = await asyncio.gather(
            member_task, clans_access_roles_task
        )

    if not member:
        return await interaction.followup.send(
            embed=EntityNotFoundEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
                "user",
            ),
        )

    if not clans_access_roles_ids:
        raise FieldNotConfiguredError("clans access")

    # === Перевірка ролей ===
    has_access_role = has_any_role_from_sequence(
        cast(discord.Member, interaction.user), clans_access_roles_ids
    )
    if not has_access_role:
        return await interaction.followup.send(
            embed=MissingPermissionsEmbed(
                bot.user.name,  # type: ignore
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

    # db transaction
    async with bot.uow.start() as session:
        try:
            clan = await create_clan(
                session,
                guild_id=guild.id,
                name=name,
                role_id=clan_role.id,
            )
            await session.flush()

        except IntegrityError:
            await session.rollback()
            try:
                asyncio.create_task(  # noqa: RUF006
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
                    f"Клан с таким именем ({name}) уже существует.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
            )

        try:
            await create_clan_member(
                session,
                guild_id=guild.id,
                clan_id=clan.id,
                user_id=leader.id,
                role=ClanMemberRoleEnum.LEADER,
            )
            await session.commit()

        except IntegrityError:
            await session.rollback()
            try:
                asyncio.create_task(  # noqa: RUF006
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
                    f"Пользователь {leader.mention} уже состоит в другом клане.",  # noqa: E501
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
            )

        except Exception as e:
            await session.rollback()
            logger.error(
                "[clans] Error creating clan in database for guild %s: %s",
                guild.id,
                e,
            )
            try:
                asyncio.create_task(  # noqa: RUF006
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

        # waiting for role assignment and db commit
        commit_task = asyncio.create_task(session.commit())
        assign_task = asyncio.create_task(
            member.add_roles(clan_role, reason="Назначение роли лидера клана.")
        )
        await asyncio.gather(commit_task, assign_task)

    logger.info(
        "[command] - invoked user=%s guild=%s clan_name=%s leader=%s color=%s",
        interaction.user.id,
        guild.id,
        name,
        leader.id,
        color_int,
    )

    return await interaction.followup.send(
        embed=SuccessMoveEmbed(
            "Клан успешно создан",
            f"Клан **{name}** успешно создан, и роль назначена пользователю {leader.mention}.",  # noqa: E501
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
    )
