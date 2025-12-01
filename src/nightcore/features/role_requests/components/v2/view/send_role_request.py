"""View for sending role requests."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Color, Guild, Member, Role, SelectOption
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

from src.infra.db.models._enums import RoleRequestStateEnum
from src.infra.db.operations import (
    get_latest_user_role_request,
    get_organization_roles_ids,
)
from src.nightcore.components.embed import (
    ErrorEmbed,
    SuccessMoveEmbed,
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


class SelectOrgRoleActionRow(ActionRow["SendRoleRequestView"]):
    def __init__(self, org_options: list[SelectOption]) -> None:
        super().__init__()

        org_select = Select["SendRoleRequestView"](
            placeholder="Выберите вашу организацию.",
            min_values=1,
            max_values=1,
            custom_id="role_request:select_org_role",
            options=org_options,
        )
        self.add_item(org_select)


class SelectIllRoleActionRow(ActionRow["SendRoleRequestView"]):
    def __init__(self, ill_options: list[SelectOption]) -> None:
        super().__init__()

        ill_select = Select["SendRoleRequestView"](
            placeholder="Выберите вашу нелегальную организацию.",
            min_values=1,
            max_values=1,
            custom_id="role_request:select_ill_role",
            options=ill_options,
        )
        self.add_item(ill_select)


class OtherRoleRequestButtons(ActionRow["SendRoleRequestView"]):
    @button(
        label="Отменить текущий запрос",
        custom_id="role_request:cancel",
        style=ButtonStyle.grey,
        emoji="<:failed:1442915170320912506>",
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
                        roles_ids=[role_id],
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
        emoji="<:idcard:1442915777593348163>",
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
        self,
        bot: "Nightcore",
        org_options: list[SelectOption] | None = None,
        ill_options: list[SelectOption] | None = None,
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot

        container = Container[Self](accent_color=Color.from_str("#515cff"))

        # header
        container.add_item(
            TextDisplay[Self](
                "## <:fingerprint:1442915534478774272> Отправить запрос на роль"  # noqa: E501
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
        if org_options:
            container.add_item(
                SelectOrgRoleActionRow(
                    org_options=org_options,
                )
            )
        if ill_options:
            container.add_item(
                SelectIllRoleActionRow(
                    ill_options=ill_options,
                )
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
