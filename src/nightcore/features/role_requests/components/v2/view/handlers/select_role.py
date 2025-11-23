"""Handle the select role interaction - shared logic."""

import asyncio
import logging
from typing import TYPE_CHECKING, cast

from discord import Guild, Member, Role, SelectOption
from discord.interactions import Interaction

from src.infra.db.models import MainGuildConfig
from src.infra.db.models._enums import ChannelType, RoleRequestStateEnum
from src.infra.db.operations import (
    get_illegal_roles_full_json,
    get_latest_user_role_request,
    get_or_create_user,
    get_organization_roles_full_json,
    get_specified_channel,
)
from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.role_requests.components.modal import (
    SendRoleRequestModal,
)

from ..check_role_request import CheckRoleRequestView

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

    from ..send_role_request import (
        SendRoleRequestView,
    )

from src.nightcore.utils import (
    ensure_messageable_channel_exists,
    ensure_role_exists,
)

logger = logging.getLogger(__name__)


async def handle_role_select_button_callback(
    interaction: Interaction["Nightcore"], view: type["SendRoleRequestView"]
) -> None:
    """Handle the select role interaction - shared logic."""
    guild = cast(Guild, interaction.guild)
    user = cast(Member, interaction.user)

    bot = interaction.client

    option_parts: list[int, str] = interaction.data.get("values")[0].split(  # type: ignore
        ","
    )
    selected_role_id = int(option_parts[0])
    selected_role_tag = option_parts[1]

    outcome = ""
    org_options: list[SelectOption] = []
    ill_options: list[SelectOption] = []
    check_role_request_channel_id = 0
    requested_role: Role | None = None
    channel = None

    async with bot.uow.start() as session:
        try:
            org_roles = await get_organization_roles_full_json(
                session, guild_id=guild.id
            )
            ill_roles = await get_illegal_roles_full_json(
                session, guild_id=guild.id
            )

            if not org_roles and not ill_roles:
                outcome = "no_org_roles"
            else:
                if org_roles:
                    org_options = [
                        SelectOption(
                            label=v["name"], value=f"{v['role_id']},{k}"
                        )
                        for k, v in org_roles.items()
                    ]
                if ill_roles:
                    ill_options = [
                        SelectOption(
                            label=v["name"], value=f"{v['role_id']},{k}"
                        )
                        for k, v in ill_roles.items()
                    ]

                dbuser, _ = await get_or_create_user(
                    session, guild_id=guild.id, user_id=user.id
                )

                if dbuser.role_request_ban:
                    outcome = "user_banned"
                else:
                    last_rr = await get_latest_user_role_request(
                        session, guild_id=guild.id, user_id=user.id
                    )

                    if (
                        last_rr
                        and last_rr.state == RoleRequestStateEnum.PENDING
                    ):
                        outcome = "pending_request_exists"
                    else:
                        check_role_request_channel_id = (
                            await get_specified_channel(
                                session,
                                guild_id=guild.id,
                                config_type=MainGuildConfig,
                                channel_type=ChannelType.ROLE_REQUESTS,
                            )
                        )

                        if not check_role_request_channel_id:
                            outcome = "channel_not_configured"
                        else:
                            outcome = "success"
        except Exception as e:
            logger.error(
                "Error handling role selection for user %s in guild %s: %s",
                user.id,
                guild.id,
                e,
            )
            outcome = "error"

    if outcome == "error":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Не удалось отправить запрос роли",
                "Произошла внутренняя ошибка при обработке вашего запроса на роль.",  # noqa: E501
                view.bot.user.name,  # type: ignore
                view.bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "no_org_roles":
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Не удалось отправить запрос роли",
                "Организационные роли не настроены на этом сервере.",
                view.bot.user.name,  # type: ignore
                view.bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "user_banned":
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Не удалось отправить запрос роли",
                "У вас имеется блокировки на подачу запросов для получение роли.",  # noqa: E501
                view.bot.user.name,  # type: ignore
                view.bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "pending_request_exists":
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Не удалось отправить запрос роли",
                "У вас уже есть активный запрос на роль.",
                view.bot.user.name,  # type: ignore
                view.bot.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "channel_not_configured":
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Не удалось отправить запрос роли",
                "Канал для проверки запросов на роли не настроен.",
                interaction.client.user.name,  # type: ignore
                interaction.client.user.display_avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    if outcome == "success":
        requested_role = await ensure_role_exists(guild, selected_role_id)
        try:
            if not requested_role:
                await asyncio.gather(
                    interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Не удалось отправить запрос роли",
                            "Выбранная роль не существует на этом сервере.",
                            view.bot.user.name,  # type: ignore
                            view.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    ),
                    interaction.message.edit(  # type: ignore
                        view=view(
                            bot,
                            org_options=org_options,
                            ill_options=ill_options if ill_options else None,
                        )
                    ),
                )
                return

            channel = await ensure_messageable_channel_exists(
                guild, cast(int, check_role_request_channel_id)
            )
            if not channel:
                await asyncio.gather(
                    interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Не удалось отправить запрос роли",
                            "Канал для проверки запросов на роли не существует или недоступен.",  # noqa: E501
                            view.bot.user.name,  # type: ignore
                            view.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    ),
                    interaction.message.edit(  # type: ignore
                        view=view(
                            bot,
                            org_options=org_options,
                            ill_options=ill_options if ill_options else None,
                        )
                    ),
                )
        except Exception as e:
            logger.error(
                "Error ensuring channel or role exists for user %s in guild %s: %s",  # noqa: E501
                user.id,
                guild.id,
                e,
            )
            return

    if not requested_role or not channel:
        # This should not happen, but just in case
        return

    await interaction.response.send_modal(
        SendRoleRequestModal(
            channel=channel,
            role=requested_role,
            bot=bot,
            selected_role_tag=cast(str, selected_role_tag),
            view=CheckRoleRequestView,
        )
    )

    logger.info(
        "User %s selected role %s in guild %s",
        user.id,
        selected_role_id,
        guild.id,
    )

    asyncio.create_task(
        interaction.message.edit(  # type: ignore
            view=view(
                bot,
                org_options=org_options,
                ill_options=ill_options if ill_options else None,
            )
        )
    )
