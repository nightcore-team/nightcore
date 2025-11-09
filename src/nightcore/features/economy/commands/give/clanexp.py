"""Command to give experience to a clan."""

from typing import TYPE_CHECKING, cast

from discord import Guild, Member, app_commands
from discord.interactions import Interaction

from src.infra.db.models import Clan, GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
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
from src.nightcore.features.clans.utils import clans_autocomplete
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.utils import has_any_role_from_sequence

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


@give_group.command(name="clanexp", description="Выдать опыт клану")
@app_commands.describe(
    clan="Клан, которому выдаётся опыт",
    amount="Количество опыта для выдачи",
)
@app_commands.autocomplete(clan=clans_autocomplete)
async def give_clanexp(
    interaction: Interaction["Nightcore"],
    clan: str,
    amount: app_commands.Range[int, -50000, 50000],
):
    """Give experience to a clan."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    user = cast(Member, interaction.user)

    outcome = ""
    db_clan: Clan | None = None

    async with bot.uow.start() as session:
        economy_access_roles_ids = await get_specified_field(
            session,
            guild_id=guild.id,
            config_type=GuildEconomyConfig,
            field_name="economy_access_roles_ids",
        )
        logging_channel_id = await get_specified_channel(
            session,
            guild_id=guild.id,
            config_type=GuildLoggingConfig,
            channel_type=ChannelType.LOGGING_CLANS,
        )
        if not economy_access_roles_ids:
            raise FieldNotConfiguredError("economy access")

        if not has_any_role_from_sequence(user, economy_access_roles_ids):
            outcome = "missing_permissions"
        else:
            db_clan = await get_clan_by_id(
                session, guild_id=guild.id, clan_id=int(clan)
            )
            if not db_clan:
                outcome = "clan_not_found"

        if not outcome:
            cast(Clan, db_clan).current_exp += amount
            await session.flush()

    if outcome == "missing_permissions":
        return await interaction.response.send_message(
            embed=MissingPermissionsEmbed(
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

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
        ),
    )
