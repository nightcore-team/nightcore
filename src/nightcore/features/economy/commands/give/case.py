"""Command to give a case to a user."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, User, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.models.user import UserCase
from src.infra.db.operations import (
    get_case_by_id,
    get_or_create_user,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.events.dto import (
    AwardNotificationEventDTO,
)
from src.nightcore.features.economy.utils.autocomplete import (
    guild_cases_autocomplete,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)
from src.nightcore.utils.transformers.str_to_int import StrToIntTransformer

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@give_group.command(name="case", description="Выдать пользователю кейс")  # type: ignore
@app_commands.describe(
    user="Пользователь, которому выдается кейс.",
    case_id="Кейс для выдачи.",
    amount="Количество кейсов для выдачи.",
    reason="Причина выдачи кейса (необязательно).",
)
@app_commands.autocomplete(case_id=guild_cases_autocomplete)
@app_commands.rename(case_id="case")
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def give_case(
    interaction: Interaction["Nightcore"],
    user: User,
    case_id: app_commands.Transform[int, StrToIntTransformer],
    amount: int,
    reason: str | None = None,
):
    """Give a case to user."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    if user == bot.user:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи кейса",
                "Невозможно выдать кейс боту.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    outcome = ""

    try:
        async with bot.uow.start() as session:
            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

            if not outcome:
                user_record, _ = await get_or_create_user(
                    session,
                    guild_id=guild.id,
                    user_id=user.id,
                    with_relations=True,
                )

                case = await get_case_by_id(
                    session, guild_id=guild.id, case_id=case_id
                )

                if case is None:
                    outcome = "unknown_case"
                else:
                    if user_case := user_record.get_case(case.id):
                        user_case.amount += amount
                    else:
                        if amount < 1:
                            outcome = "cannot_give_negative_amount"
                        else:
                            new_case = UserCase(
                                case_id=case.id,
                                amount=amount,
                                user_id=user.id,
                                guild_id=guild.id,
                            )

                            session.add(new_case)

                    if not outcome:
                        outcome = "success"

    except Exception as e:
        logger.exception(
            "[give/case] Error giving case %s to user %s in guild %s: %s",
            case_id,
            user.id,
            guild.id,
            e,
        )
        outcome = "give_case_error"

    if outcome == "unknown_case":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи кейса",
                "Кейс не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "cannot_give_negative_amount":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи кейса",
                "Невозможно выдать отрицательное количество.\n"
                "(Отрицательное количество может использоваться только для снятия кейсов)",  # noqa: E501
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "give_case_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи кейса",
                "Не удалось выдать кейс пользователю.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        await interaction.response.send_message(
            embed=SuccessMoveEmbed(
                "Выдача кейса успешна",
                f"Вы успешно выдали пользователю <@{user.id}> "
                f"**{case.name}** в количестве **{amount}**.",  # type: ignore
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

        bot.dispatch(
            "user_items_changed",
            dto=AwardNotificationEventDTO(
                guild=guild,
                event_type="give/case",
                logging_channel_id=logging_channel_id,  # type: ignore
                user_id=user.id,
                moderator_id=interaction.user.id,
                item_name=case.name,  # type: ignore
                amount=amount,
                reason=reason,
            ),
        )
