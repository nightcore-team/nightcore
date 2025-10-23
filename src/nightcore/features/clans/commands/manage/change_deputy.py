"""Clan creation command."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models._enums import ClanMemberRoleEnum
from src.infra.db.operations import (
    get_clan_member,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans._groups import manage as manage_clan_group

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@manage_clan_group.command(
    name="change_deputy", description="Change the clan deputy. (Add/remove)"
)
@app_commands.choices(
    option=[
        app_commands.Choice(name="Назначить", value="add"),
        app_commands.Choice(name="Снять", value="remove"),
    ]
)
@app_commands.describe()
async def change_deputy(
    interaction: Interaction["Nightcore"],
    member: Member,
    option: str,
):
    """Change the clan deputy."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)
    user = cast(Member, interaction.user)

    if user == member:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка изменения заместителя",
                "Вы не можете изменить свою собственную роль.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with bot.uow.start() as session:
        # get clanmember
        leader = await get_clan_member(
            session,
            guild_id=guild.id,
            user_id=user.id,
            with_relations=True,
        )
        if not leader:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка изменения заместителя",
                    "Вы не состоите в клане.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if leader.role != ClanMemberRoleEnum.LEADER:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        clan_member = await get_clan_member(
            session,
            guild_id=guild.id,
            user_id=member.id,
        )
        if not clan_member or clan_member.clan_id != leader.clan_id:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка изменения заместителя",
                    "Указанный пользователь не состоит в вашем клане.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        match option:
            case "add":
                if len(leader.clan.deputies) + 1 > leader.clan.max_deputies:
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка изменения заместителя",
                            "Превышено максимальное количество заместителей в клане.",
                            bot.user.display_name,  # type: ignore
                            bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                if clan_member.role == ClanMemberRoleEnum.DEPUTY:
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка изменения заместителя",
                            "Указанный пользователь уже является заместителем.",  # noqa: E501
                            bot.user.display_name,  # type: ignore
                            bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                clan_member.role = ClanMemberRoleEnum.DEPUTY
            case "remove":
                if clan_member.role != ClanMemberRoleEnum.DEPUTY:
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка изменения заместителя",
                            "Указанный пользователь не является заместителем.",
                            bot.user.display_name,  # type: ignore
                            bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                clan_member.role = ClanMemberRoleEnum.MEMBER
            case _:
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка изменения заместителя",
                        "Неверная опция. Используйте 'add' или 'remove'.",
                        bot.user.display_name,  # type: ignore
                        bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

        await session.flush()

    return await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Изменение заместителя",
            f"Роль пользователя **{member.display_name}** успешно изменена на **{clan_member.role.value.lower()}**.",  # noqa: E501
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )
