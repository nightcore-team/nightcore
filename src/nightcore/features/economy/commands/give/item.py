"""Command to give selected economy item to all users with a role."""

import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Role, app_commands
from discord.interactions import Interaction

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.models._enums import CaseDropTypeEnum
from src.infra.db.models.user import UserCase
from src.infra.db.operations import (
    get_case_by_id,
    get_color_by_id,
    get_or_create_user,
    get_specified_guild_config,
)
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.economy._groups import give as give_group
from src.nightcore.features.economy.utils.autocomplete import (
    reward_depends_on_type_autocomplete,
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
    reward_id="Кейс/цвет для выдачи (обязательно для case/color).",
    reason="Причина выдачи (необязательно).",
)
@app_commands.autocomplete(reward_id=reward_depends_on_type_autocomplete)
@app_commands.rename(item_type="type", reward_id="reward")
@check_required_permissions(PermissionsFlagEnum.ECONOMY_ACCESS)
async def give_item(
    interaction: Interaction["Nightcore"],
    role: Role,
    item_type: CaseDropTypeEnum,
    amount: app_commands.Range[int, 1, 50000],
    reward_id: str | None = None,
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
    try:
        async with bot.uow.start() as session:
            selected_case = None
            selected_color = None
            if item_type == CaseDropTypeEnum.CUSTOM:
                outcome = "custom_type_not_supported"
            elif item_type == CaseDropTypeEnum.CASE:
                if reward_id is None:
                    outcome = "missing_reward_id"
                else:
                    selected_case = await get_case_by_id(
                        session,
                        guild_id=guild.id,
                        case_id=int(reward_id),
                    )
                    if selected_case is None:
                        outcome = "unknown_case"
                    else:
                        item_name = selected_case.name

            elif item_type == CaseDropTypeEnum.COLOR:
                if reward_id is None:
                    outcome = "missing_reward_id"
                else:
                    selected_color = await get_color_by_id(
                        session,
                        guild_id=guild.id,
                        color_id=int(reward_id),
                    )
                    if selected_color is None:
                        outcome = "unknown_color"
                    else:
                        color_role = guild.get_role(selected_color.role_id)
                        item_name = (
                            f"{color_role.name} ({selected_color.role_id})"
                            if color_role
                            else f"color ({selected_color.role_id})"
                        )

            elif item_type == CaseDropTypeEnum.COINS:
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
            elif item_type == CaseDropTypeEnum.EXP:
                item_name = "опыт"
            elif item_type == CaseDropTypeEnum.BATTLEPASS_POINTS:
                item_name = "очки батлпасса"

            if not outcome:
                for member in target_members:
                    user_record, _ = await get_or_create_user(
                        session,
                        guild_id=guild.id,
                        user_id=member.id,
                        with_relations=item_type
                        in {CaseDropTypeEnum.CASE, CaseDropTypeEnum.COLOR},
                    )

                    if item_type == CaseDropTypeEnum.COINS:
                        user_record.coins += amount
                    elif item_type == CaseDropTypeEnum.EXP:
                        user_record.current_exp += amount
                    elif item_type == CaseDropTypeEnum.BATTLEPASS_POINTS:
                        user_record.battle_pass_points += amount
                    elif (
                        item_type == CaseDropTypeEnum.CASE
                        and selected_case is not None
                    ):
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
                    elif (
                        item_type == CaseDropTypeEnum.COLOR
                        and selected_color is not None
                        and selected_color not in user_record.colors
                    ):
                        user_record.colors.append(selected_color)

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

    if outcome == "custom_type_not_supported":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи",
                "Выбранный тип не поддерживается для массовой выдачи.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "missing_reward_id":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи",
                "Для выбранного типа нужно указать корректный reward.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome in {"invalid_case", "unknown_case"}:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи",
                "Кейс с указанным id не найден.",
                bot.user.display_name,  # type: ignore
                bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "unknown_color":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка выдачи",
                "Цвет с указанным id не найден.",
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
