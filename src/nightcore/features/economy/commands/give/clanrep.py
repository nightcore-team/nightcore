"""Give clan reputation command."""

from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import get_clan_by_id, get_specified_field
from src.nightcore.components.embed import (
    ErrorEmbed,
    MissingPermissionsEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.clans.utils import clans_autocomplete
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.utils import has_any_role_from_sequence

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@give_group.command(name="clanrep", description="Give reputation to a clan.")
@app_commands.describe()
@app_commands.autocomplete(clan=clans_autocomplete)
async def give_clanrep(
    interaction: Interaction["Nightcore"],
    clan: str,
    amount: int,
):
    """Give reputation to a clan."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    user = cast(Member, interaction.user)

    async with bot.uow.start() as session:
        economy_access_roles_ids = await get_specified_field(
            session,
            guild_id=guild.id,
            config_type=GuildEconomyConfig,
            field_name="economy_access_roles_ids",
        )
        if not economy_access_roles_ids:
            raise FieldNotConfiguredError("economy access")

        if not has_any_role_from_sequence(user, economy_access_roles_ids):
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        db_clan = await get_clan_by_id(
            session, guild_id=guild.id, clan_id=int(clan)
        )
        if not db_clan:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка выдачи клановой репутации",
                    "Клан не найден на этом сервере.",
                    bot.user.display_name,  # type: ignore
                    bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        db_clan.coins += amount
        await session.flush()

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Выдача клановой репутации",
            f"Успешно выдано {amount} репутации клану **{db_clan.name}**.",
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )
