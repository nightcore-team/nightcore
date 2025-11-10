"""View for sending role requests."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Guild, Member, Role, SelectOption
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Select,
    Separator,
    TextDisplay,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models import MainGuildConfig
from src.infra.db.models._enums import ChannelType, RoleRequestStateEnum
from src.infra.db.operations import (
    get_latest_user_role_request,
    get_or_create_user,
    get_organization_roles_full_json,
    get_organization_roles_ids,
    get_specified_channel,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
)
from src.nightcore.features.role_requests.components.modal import (
    SendRoleRequestModal,
)
from src.nightcore.features.role_requests.components.v2.view.check_role_request import (  # noqa: E501
    CheckRoleRequestView,
)
from src.nightcore.features.role_requests.components.v2.view.role_request_state import (  # noqa: E501
    RoleRequestStateView,
)
from src.nightcore.utils import (
    discord_ts,
    ensure_message_exists,
    ensure_messageable_channel_exists,
    ensure_role_exists,
    has_any_role_from_sequence,
)

logger = logging.getLogger(__name__)


# SelectOption: label, value
class SelectRoleActionRow(ActionRow["SendRoleRequestView"]):
    def __init__(self, options: list[SelectOption]) -> None:
        super().__init__()

        select = Select["SendRoleRequestView"](
            placeholder="Select your organization.",
            min_values=1,
            max_values=1,
            custom_id="role_request:select_role",
            options=options,
        )

        select.callback = self.select_role

        self.add_item(select)

    async def select_role(self, interaction: Interaction["Nightcore"]) -> None:
        """Handle the select role interaction."""
        guild = cast(Guild, interaction.guild)
        view = cast(SendRoleRequestView, self.view)
        user = cast(Member, interaction.user)

        option_parts: list[int, str] = interaction.data.get("values")[0].split(  # type: ignore
            ","
        )
        selected_role_id = int(option_parts[0])
        selected_role_tag = option_parts[1]

        outcome = ""
        options: list[SelectOption] = []
        check_role_request_channel_id = 0

        async with view.bot.uow.start() as session:
            org_roles = await get_organization_roles_full_json(
                session, guild_id=guild.id
            )

            if not org_roles:
                outcome = "no_org_roles"
            else:
                options = [
                    SelectOption(label=v["name"], value=f"{v['role_id']},{k}")
                    for k, v in org_roles.items()
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
                        view=SendRoleRequestView(view.bot, options=options)
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
                        view=SendRoleRequestView(view.bot, options=options)
                    ),
                )
                return

            await interaction.response.send_modal(
                SendRoleRequestModal(
                    channel=channel,
                    role=requested_role,
                    bot=view.bot,
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
                view=SendRoleRequestView(view.bot, options=options)
            )
        )


class OtherRoleRequestButtons(ActionRow["SendRoleRequestView"]):
    @button(
        label="Отменить текущий запрос",
        custom_id="role_request:cancel",
        style=ButtonStyle.grey,
        emoji="<:9349_nope:1414732960841859182>",
    )
    async def cancel_role_request(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["SendRoleRequestView"],
    ) -> None:
        """Handle the cancel button interaction."""

        guild = cast(Guild, interaction.guild)
        user = cast(Member, interaction.user)
        view = cast(SendRoleRequestView, self.view)

        await interaction.response.defer(thinking=True, ephemeral=True)

        outcome = ""
        channel_id = 0
        message_id = 0
        role_id = 0
        moderator_id: int | None = None

        async with view.bot.uow.start() as session:
            last_rr = await get_latest_user_role_request(
                session, guild_id=guild.id, user_id=user.id
            )

            if not last_rr or last_rr.state in (
                RoleRequestStateEnum.CANCELED,
                RoleRequestStateEnum.DENIED,
                RoleRequestStateEnum.APPROVED,
            ):
                outcome = "no_active_request"
            else:
                channel_id = last_rr.channel_id
                message_id = last_rr.message_id
                role_id = last_rr.role_id
                moderator_id = last_rr.moderator_id

                await session.delete(last_rr)

                outcome = "success"

        if outcome == "no_active_request":
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка при отмене запроса",
                    "У вас нет активных запросов на роль.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
            )

        if outcome == "success":
            channel = await ensure_messageable_channel_exists(
                guild, channel_id
            )
            if not channel:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка при отмене запроса",
                        "Канал для проверки запросов на роль не существует или недоступен.",  # noqa: E501
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            rr_message = await ensure_message_exists(
                view.bot, channel, message_id
            )
            if not rr_message:
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка при отмене запроса",
                        "Сообщение с вашим запросом на роль не найдено.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            try:
                message = await rr_message.edit(
                    view=CheckRoleRequestView(
                        bot=view.bot,
                        interaction_user_id=user.id,
                        interaction_user_nick=user.display_name,
                        role_requested_id=role_id,
                        moderator_id=moderator_id,
                        state=RoleRequestStateEnum.CANCELED,
                        all_disabled=True,
                    )
                )
            except Exception as e:
                logger.error(
                    "Failed to update role request message %s in guild %s: %s",
                    message_id,
                    guild.id,
                    e,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка при отмене запроса",
                        "Произошла ошибка при обновлении сообщения с вашим запросом на роль.",  # noqa: E501
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            try:
                await message.reply(
                    view=RoleRequestStateView(
                        bot=view.bot,
                        moderator_id=cast(int, moderator_id),
                        user_id=user.id,
                        state=RoleRequestStateEnum.CANCELED,
                        role_id=role_id,
                    )
                )
            except Exception as e:
                logger.error(
                    "Failed to reply to role request message %s in guild %s: %s",  # noqa: E501
                    message.id,
                    guild.id,
                    e,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Ошибка при отмене запроса",
                        "Произошла ошибка при отправке сообщения об отмене вашего запроса на роль.",  # noqa: E501
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    )
                )

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Запрос отменен",
                    "Вы успешно отменили свой запрос на роль.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                )
            )

            logger.info(
                "User %s canceled role request in guild %s",
                user.id,
                guild.id,
            )

    @button(
        label="Снять организационные роли",
        custom_id="role_request:remove_roles",
        style=ButtonStyle.grey,
        emoji="<:42276rank:1420074588104294440>",
    )
    async def remove_organization_roles(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["SendRoleRequestView"],
    ) -> None:
        """Handle the remove roles button interaction."""

        guild = cast(Guild, interaction.guild)
        view = cast(SendRoleRequestView, self.view)
        user = cast(Member, interaction.user)

        outcome = ""
        org_roles_ids: list[int] = []

        async with view.bot.uow.start() as session:
            org_roles_ids = await get_organization_roles_ids(
                session, guild_id=guild.id
            )

            if not org_roles_ids:
                outcome = "no_org_roles_configured"
            else:
                outcome = "success"

        if outcome == "no_org_roles_configured":
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Не удалось снять организационные роли",
                    "Организационные роли не настроены на этом сервере.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        if outcome == "success":
            if not has_any_role_from_sequence(user, org_roles_ids):
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Не удалось снять организационные роли",
                        "У вас нет ролей для снятия.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            await interaction.response.defer(thinking=True, ephemeral=True)

            roles_to_remove: list[Role] = []
            for role_id in org_roles_ids:
                role = await ensure_role_exists(guild, role_id)
                if role and role in user.roles:
                    roles_to_remove.append(role)

            try:
                await user.remove_roles(
                    *roles_to_remove, reason="Снятие организационных ролей"
                )
            except Exception as e:
                logger.error(
                    "Failed to remove organization roles from user %s in guild %s: %s",  # noqa: E501
                    user.id,
                    guild.id,
                    e,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Не удалось снять организационные роли",
                        "Произошла ошибка при снятии ваших ролей.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                )

            await interaction.followup.send(
                embed=SuccessMoveEmbed(
                    "Снятие ролей успешно",
                    f"Ваши организационные роли ({', '.join(f'<@&{role.id}>' for role in roles_to_remove)}) были сняты.",  # noqa: E501
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
            )

            logger.info(
                "User %s removed organization roles in guild %s: %s",
                user.id,
                guild.id,
                [role.id for role in roles_to_remove],
            )


class SendRoleRequestView(LayoutView):
    def __init__(
        self, bot: "Nightcore", options: list[SelectOption] | None = None
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot

        container = Container[Self]()

        # header
        container.add_item(
            TextDisplay[Self](
                "## <:72151staff:1421169506230866050> Отправить запрос на роль"
            )
        )
        container.add_item(Separator[Self]())

        # main text
        container.add_item(
            TextDisplay[Self](
                "**Для запроса роли, пожалуйста, выберите вашу организацию...**\n"  # noqa: E501
                "**...из списка ниже.**"
            )
        )

        # select
        container.add_item(
            SelectRoleActionRow(options=cast(list[SelectOption], options))
        )
        container.add_item(Separator[Self]())

        # other buttons
        container.add_item(OtherRoleRequestButtons())
        container.add_item(Separator[Self]())

        # footer
        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)
