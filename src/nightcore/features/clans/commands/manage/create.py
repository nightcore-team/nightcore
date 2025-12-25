"""Clan creation command."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

import discord
from discord import Guild, Member, app_commands
from discord.interactions import Interaction
from sqlalchemy.exc import IntegrityError

from src.infra.db.models._enums import ClanMemberRoleEnum
from src.infra.db.operations import (
    create_clan,
    create_clan_member,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans._groups import manage as manage_clan_group
from src.nightcore.utils import (
    safe_delete_role,
)
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
)
@check_required_permissions(PermissionsFlagEnum.CLANS_ACCESS)
async def create(
    interaction: Interaction["Nightcore"],
    name: app_commands.Range[str, 1, 100],
    leader: Member,
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

    return await interaction.followup.send(
        embed=SuccessMoveEmbed(
            "Клан успешно создан",
            f"Клан **{name}** успешно создан, и роль назначена пользователю {leader.mention}.",  # noqa: E501
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
    )
