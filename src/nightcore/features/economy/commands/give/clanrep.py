"""Command to give reputation to a clan."""

from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    get_clan_by_id,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans.events.dto import (
    AwardNotificationEventDTO,
)
from src.nightcore.features.clans.utils import clans_autocomplete
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@give_group.command(name="clanrep", description="Выдать репутацию клану")  # type: ignore
@app_commands.describe(
    clan="Клан, которому выдаётся репутация",
    amount="Количество репутации для выдачи",
)
@app_commands.autocomplete(clan=clans_autocomplete)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def give_clanrep(
    interaction: Interaction["Nightcore"],
    clan: str,
    amount: app_commands.Range[int, -50000, 50000],
):
    """Give reputation to a clan."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    user = cast(Member, interaction.user)

    outcome = ""
    async with bot.uow.start() as session:
        logging_channel_id = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_CLANS,
        )

        db_clan = await get_clan_by_id(
            session, guild_id=guild.id, clan_id=int(clan)
        )
        if not db_clan:
            outcome = "clan_not_found"

        if not outcome:
            db_clan.coins += amount  # type: ignore
            await session.flush()
            outcome = "success"

    if outcome == "clan_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи клановой репутации",
                "Клан не найден в базе данных.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Выдача клановой репутации",
            f"Успешно выдано {amount} репутации клану **{db_clan.name}**.",  # type: ignore
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    bot.dispatch(
        "clan_items_changed",
        dto=AwardNotificationEventDTO(
            guild=guild,
            event_type="give/clanrep",
            logging_channel_id=logging_channel_id,
            user_id=user.id,
            moderator_id=interaction.user.id,
            item_name="репутация",
            amount=amount,
        ),
    )
