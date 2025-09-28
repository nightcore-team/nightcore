"""View for sending role requests."""

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
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.role_requests.components.modal import (
    SendRoleRequestModal,
)
from src.nightcore.features.role_requests.components.v2.view.check_role_request import (
    CheckRoleRequestView,
)
from src.nightcore.utils import (
    discord_ts,
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

        option_parts: list[str] = interaction.data.get("values")[0].split(",")  # type: ignore
        selected_role_id = int(option_parts[0])  # type: ignore
        selected_role_tag = option_parts[1]  # type: ignore

        async with view.bot.uow.start() as session:
            org_roles = await get_organization_roles_full_json(
                session, guild_id=guild.id
            )
            if not org_roles:
                raise FieldNotConfiguredError("organization roles")

            options = [
                SelectOption(label=v["name"], value=f"{v['role_id']},{k}")
                for k, v in org_roles.items()
            ]

            dbuser, _ = await get_or_create_user(
                session, guild_id=guild.id, user_id=user.id
            )
            if dbuser.role_request_ban:
                await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Role Request Failed",
                        "You are banned from requesting roles.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                await interaction.message.edit(
                    view=SendRoleRequestView(view.bot, options=options)
                )
                return

            last_rr = await get_latest_user_role_request(
                session, guild_id=guild.id, user_id=user.id
            )
            if last_rr and last_rr.state in (
                RoleRequestStateEnum.PENDING,
                RoleRequestStateEnum.REQUESTED,
                RoleRequestStateEnum.STATS_PROVIDED,
            ):
                await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Role Request Failed",
                        "You already have a pending role request.",
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                await interaction.message.edit(
                    view=SendRoleRequestView(view.bot, options=options)
                )
                return

            check_role_request_channel_id = await get_specified_channel(
                session,
                guild_id=guild.id,
                config_type=MainGuildConfig,
                channel_type=ChannelType.ROLE_REQUESTS,
            )
            if not check_role_request_channel_id:
                await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Field not configured.",
                        "Channel for checking role requests is not configured.",  # noqa: E501
                        interaction.client.user.name,  # type: ignore
                        interaction.client.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                await interaction.message.edit(
                    view=SendRoleRequestView(view.bot, options=options)
                )
                return

        requested_role = await ensure_role_exists(guild, selected_role_id)
        if not requested_role:
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Role Request Failed",
                    "The selected role does not exist in this server.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            await interaction.message.edit(
                view=SendRoleRequestView(view.bot, options=options)
            )
            return

        channel = await ensure_messageable_channel_exists(
            guild, check_role_request_channel_id
        )
        if not channel:
            await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Role Request Failed",
                    "The checking role requests channel does not exist or is not accessible.",  # noqa: E501
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )
            await interaction.message.edit(
                view=SendRoleRequestView(view.bot, options=options)
            )
            return

        await interaction.response.send_modal(
            SendRoleRequestModal(
                user=user,
                channel=channel,
                role=requested_role,
                bot=view.bot,
                selected_role_tag=selected_role_tag,  # type: ignore
                view=CheckRoleRequestView,
            )
        )

        await interaction.message.edit(
            view=SendRoleRequestView(view.bot, options=options)
        )

        logger.info(
            "User %s selected role %s in guild %s",
            interaction.user.id,
            selected_role_id,
            guild.id,
        )


class OtherRoleRequestButtons(ActionRow["SendRoleRequestView"]):
    @button(
        label="Отклонить текущий запрос",
        custom_id="role_request:cancel",
        style=ButtonStyle.grey,
        emoji="<:9349_nope:1414732960841859182>",
    )  # TODO: implement
    async def cancel_role_request(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["SendRoleRequestView"],
    ) -> None:
        """Handle the cancel button interaction."""
        await interaction.response.send_message(
            "Your role request has been cancelled.", ephemeral=True
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

        async with view.bot.uow.start() as session:
            if not (
                org_roles_ids := await get_organization_roles_ids(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("organization roles")

        if not has_any_role_from_sequence(user, org_roles_ids):
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Role Removal Failed",
                    "You do not have any organization roles to remove.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await interaction.response.defer(thinking=True, ephemeral=True)

        roles_to_remove: list[Role] = []
        for role_id in org_roles_ids:
            role = guild.get_role(role_id)
            if role and role in user.roles:
                roles_to_remove.append(role)

        try:
            await user.remove_roles(
                *roles_to_remove, reason="User requested role removal"
            )
        except Exception as e:
            logger.error(
                "Failed to remove organization roles from user %s in guild %s: %s",  # noqa: E501
                user.id,
                guild.id,
                e,
            )
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Role Removal Failed",
                    "An error occurred while removing your organization roles.",  # noqa: E501
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        await interaction.followup.send(
            embed=SuccessMoveEmbed(
                "Role Removal Successful",
                f"Your organization roles ({', '.join(f'<@&{role.id}>' for role in roles_to_remove)}) have been removed.",  # noqa: E501
                view.bot.user.name,  # type: ignore
                view.bot.user.display_avatar.url,  # type: ignore
            ),
        )
        logger.info(
            "[role_request:remove_roles] - invoked user=%s guild=%s",
            user.id,
            guild.id,
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
