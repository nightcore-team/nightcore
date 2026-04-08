"""Command to give selected economy item to all users with a role."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Role, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig, GuildLoggingConfig
from src.infra.db.models._enums import ChannelType
from src.infra.db.models.user import UserCase
from src.infra.db.operations import (
    get_case_by_id,
    get_or_create_user,
    get_specified_channel,
    get_specified_guild_config,
)
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.events.dto import AwardNotificationEventDTO
from src.nightcore.features.economy.utils.autocomplete import (
    guild_cases_autocomplete,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


logger = logging.getLogger(__name__)


@give_group.command(name="item", description="Выдать предмет/валюту по роли")  # type: ignore
@app_commands.describe(
    role="Роль пользователей для выдачи.",
    item_type="Тип предмета/валюты для выдачи.",
    amount="Количество для выдачи каждому пользователю.",
    case_id="Кейс для выдачи (обязательно только для типа case).",
    reason="Причина выдачи (необязательно).",
)
@app_commands.choices(
    item_type=[
        app_commands.Choice(name="Кейс", value="case"),
        app_commands.Choice(name="Коины", value="coins"),
        app_commands.Choice(name="Опыт", value="exp"),
        app_commands.Choice(name="Очки батлпасса", value="bp_coins"),
    ]
)
@app_commands.autocomplete(case_id=guild_cases_autocomplete)
@app_commands.rename(item_type="type", case_id="case")
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def give_item(
    interaction: Interaction["Nightcore"],
    role: Role,
    item_type: str,
    amount: app_commands.Range[int, 1, 50000],
    case_id: str | None = None,
    reason: str | None = None,
):
    """Give selected economy item to all members with the specified role."""

    guild = cast(Guild, interaction.guild)
    bot = interaction.client

    target_members = [
        member
        for member in role.members
        if not member.bot and member != bot.user
    ]

    if not target_members:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи",
                "У выбранной роли нет подходящих пользователей для выдачи.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    outcome = ""
    item_name = ""
    logging_channel_id: int | None = None

    try:
        async with bot.uow.start() as session:
            logging_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=GuildLoggingConfig,
                channel_type=ChannelType.LOGGING_ECONOMY,
            )

            selected_case = None
            if item_type == "case":
                if case_id is None:
                    outcome = "missing_case"
                else:
                    selected_case = await get_case_by_id(
                        session,
                        guild_id=guild.id,
                        case_id=int(case_id),
                    )
                    if selected_case is None:
                        outcome = "unknown_case"
                    else:
                        item_name = selected_case.name

            elif item_type == "coins":
                guild_config = await get_specified_guild_config(
                    session,
                    guild_id=guild.id,
                    config_type=GuildEconomyConfig,
                )
                item_name = (
                    guild_config.coin_name or "коины"
                    if guild_config
                    else "коины"
                )
            elif item_type == "exp":
                item_name = "опыт"
            elif item_type == "bp_coins":
                item_name = "очки батлпасса"

            if not outcome:
                for member in target_members:
                    user_record, _ = await get_or_create_user(
                        session,
                        guild_id=guild.id,
                        user_id=member.id,
                        with_relations=item_type == "case",
                    )

                    if item_type == "coins":
                        user_record.coins += amount
                    elif item_type == "exp":
                        user_record.current_exp += amount
                    elif item_type == "bp_coins":
                        user_record.battle_pass_points += amount
                    elif item_type == "case" and selected_case is not None:
                        user_case = user_record.get_case(selected_case.id)
                        if user_case:
                            user_case.amount += amount
                        else:
                            session.add(
                                UserCase(
                                    case_id=selected_case.id,
                                    amount=amount,
                                    user_id=member.id,
                                    guild_id=guild.id,
                                )
                            )

                outcome = "success"

    except ValueError:
        outcome = "invalid_case"
    except Exception as e:
        logger.exception(
            "[give/item] Failed to give %s to role %s in guild %s: %s",
            item_type,
            role.id,
            guild.id,
            e,
        )
        outcome = "give_item_error"

    if outcome in {"missing_case", "invalid_case", "unknown_case"}:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи",
                "Для типа case нужно указать корректный кейс.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "give_item_error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи",
                "Не удалось выдать предмет/валюту "
                "пользователям с указанной ролью.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Выдача успешна",
            f"Вы успешно выдали **{amount} {item_name}** пользователям с ролью {role.mention}.\n"  # noqa: E501
            f"Всего затронуто пользователей: **{len(target_members)}**.",
            bot.user.display_name,  # type: ignore
            bot.user.display_avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    # for member in target_members:
    #     bot.dispatch(
    #         "user_items_changed",
    #         dto=AwardNotificationEventDTO(
    #             guild=guild,
    #             event_type=f"give/item/{item_type}",
    #             logging_channel_id=logging_channel_id,
    #             user_id=member.id,
    #             moderator_id=interaction.user.id,
    #             item_name=item_name,
    #             amount=amount,
    #             reason=reason,
    #         ),
    #     )
