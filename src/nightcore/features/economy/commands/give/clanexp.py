"""Command to give experience to a clan."""

from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models import Clan, GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.operations import (
    get_clan_by_id,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.clans.utils import clans_autocomplete
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@give_group.command(name="clanexp", description="Выдать опыт клану")  # type: ignore
@app_commands.describe(
    clan="Клан, которому выдаётся опыт",
    amount="Количество опыта для выдачи",
)
@app_commands.autocomplete(clan=clans_autocomplete)
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def give_clanexp(
    interaction: Interaction["Nightcore"],
    clan: str,
    amount: app_commands.Range[int, -50000, 50000],
    reason: str | None = None,
):
    """Give experience to a clan."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    user = cast(Member, interaction.user)

    outcome = ""
    db_clan: Clan | None = None

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
            cast(Clan, db_clan).current_exp += amount
            await session.flush()

    if outcome == "clan_not_found":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи кланового опыта",
                "Клан не найден на сервере.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Выдача кланового опыта",
            f"Успешно выдано {amount} опыта клану **{cast(Clan, db_clan).name}**.",  # noqa: E501
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    bot.dispatch(
        "clan_items_changed",
        dto=AwardNotificationEventDTO(
            guild=guild,
            event_type="give/clanexp",
            logging_channel_id=logging_channel_id,
            user_id=user.id,
            moderator_id=interaction.user.id,
            item_name="клановый опыт",
            amount=amount,
            reason=reason,
        ),
    )
