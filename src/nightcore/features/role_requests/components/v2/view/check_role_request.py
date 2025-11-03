"""View for sending role requests."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Guild, MediaGalleryItem
from discord.components import (
    TextDisplay as TextDisplayOverride,
)
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    Item,
    LayoutView,
    MediaGallery,
    Separator,
    TextDisplay,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.models import GuildNotificationsConfig
from src.infra.db.models._enums import ChannelType, RoleRequestStateEnum
from src.infra.db.operations import (
    get_latest_user_role_request,
    get_specified_channel,
)
from src.nightcore.components.embed import ErrorEmbed, MissingPermissionsEmbed
from src.nightcore.features.role_requests.components.modal.decline import (
    DeclineRoleRequestModal,
)
from src.nightcore.features.role_requests.utils import send_role_request_dm
from src.nightcore.features.tickets.utils import extract_id_from_str
from src.nightcore.utils import (
    discord_ts,
    ensure_member_exists,
    ensure_role_exists,
)

from .role_request_state import RoleRequestStateView

logger = logging.getLogger(__name__)


class ManageRoleRequestActionRow(ActionRow["CheckRoleRequestView"]):
    # @button(
    #     label="Запросить статистику",
    #     custom_id="role_request:stats",
    #     style=ButtonStyle.grey,
    #     emoji="<:72151staff:1421169506230866050>",
    # )
    # async def request_stats(
    #     self,
    #     interaction: Interaction["Nightcore"],
    #     button: Button["CheckRoleRequestView"],
    # ) -> None:
    #     """Handle the cancel button interaction."""
    #     guild = cast(Guild, interaction.guild)
    #     view = cast("CheckRoleRequestView", self.view)
    #     view.state = RoleRequestStateEnum.REQUESTED
    #     view.moderator_id = interaction.user.id

    #     await interaction.response.defer()

    #     # connect information from components
    #     for component in interaction.message.components:  # type: ignore
    #         for item in component.children:  # type: ignore
    # if isinstance(item, TextDisplayOverride):
    #                 if "User | ID" in item.content:
    #                     content = item.content
    #                     content_parts = content.split("\n")
    #                     view.interaction_user_id = extract_id_from_str(
    #                         content_parts[0].split("|")[1].strip()
    #                     )
    #                     view.interaction_user_nick = (
    #                         content_parts[1].split(":")[1].strip()
    #                     )
    #                     view.role_requested_id = extract_id_from_str(
    #                         content_parts[2].split(":")[1].strip()
    #                     )
    #                     break

    #     member = await ensure_member_exists(
    #         guild,
    #         cast(int, view.interaction_user_id),
    #     )
    #     if not member:
    #         return await interaction.followup.send(
    #             embed=ErrorEmbed(
    #                 "Request stat failed",
    #                 "Cannot find this user in guild.",
    #                 view.bot.user.name,  # type: ignore
    #                 view.bot.user.display_avatar.url,  # type: ignore
    #             ),
    #             ephemeral=True,
    #         )

    #     async with view.bot.uow.start() as session:
    #         try:
    #             last_rr = await get_latest_user_role_request(
    #                 session,
    #                 guild_id=guild.id,
    #                 user_id=cast(int, view.interaction_user_id),
    #             )
    #             if not last_rr:
    #                 return await interaction.followup.send(
    #                     embed=ErrorEmbed(
    #                         "Request stat failed",
    #                         "Cannot find this role request in database.",
    #                         view.bot.user.name,  # type: ignore
    #                         view.bot.user.display_avatar.url,  # type: ignore
    #                     ),
    #                     ephemeral=True,
    #                 )

    #             if last_rr.state == RoleRequestStateEnum.REQUESTED:
    #                 return await interaction.followup.send(
    #                     embed=ErrorEmbed(
    #                         "Request stat failed",
    #                         "Another moderator is already processing this request.",  # noqa: E501
    #                         view.bot.user.name,  # type: ignore
    #                         view.bot.user.display_avatar.url,  # type: ignore
    #                     ),
    #                     ephemeral=True,
    #                 )

    #             last_rr.state = RoleRequestStateEnum.REQUESTED
    #             last_rr.moderator_id = interaction.user.id

    #             nightcore_notifications_channel_id = (
    #                 await get_specified_channel(
    #                     session,
    #                     guild_id=guild.id,
    #                     config_type=GuildNotificationsConfig,
    #                     channel_type=ChannelType.NIGHTCORE_NOTIFICATIONS,
    #                 )
    #             )

    #         except Exception as e:
    #             logger.exception(
    #                 "Failed to get role request from %s in %s: %s",
    #                 view.interaction_user_id,
    #                 guild.id,
    #                 e,
    #             )
    #             return await interaction.followup.send(
    #                 embed=ErrorEmbed(
    #                     "Request stat failed",
    #                     "An error occurred while fetching the role request from the database.",  # noqa: E501
    #                     view.bot.user.name,  # type: ignore
    #                     view.bot.user.display_avatar.url,  # type: ignore
    #                 ),
    #                 ephemeral=True,
    #             )

    #     # change button to disabled
    #     view = view.make_component()
    #     stats_button = view.get_component("role_request:stats")
    #     if not isinstance(stats_button, Button):
    #         return
    #     stats_button.disabled = True
    #     await interaction.message.edit(view=view)  # type: ignore

    #     await interaction.followup.send(
    #         view=RoleRequestStateView(
    #             bot=view.bot,
    #             moderator_id=interaction.user.id,
    #             user_id=cast(int, view.interaction_user_id),
    #             state=RoleRequestStateEnum.REQUESTED,
    #         )
    #     )

    #     await send_role_request_dm(
    #         moderator_id=interaction.user.id,
    #         reserve_channel=nightcore_notifications_channel_id,
    #         user=member,
    #         state=RoleRequestStateEnum.REQUESTED,
    #     )

    #     logger.info(
    #         "Moderator %s requested stats from user %s in guild %s",
    #         interaction.user.id,
    #         view.interaction_user_id,
    #         guild.id,
    #     )

    @button(
        label="Одобрить запрос",
        custom_id="role_request:approve",
        style=ButtonStyle.grey,
        emoji="<:52104checkmark:1414732973005340672>",
    )
    async def approve_role_request(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["CheckRoleRequestView"],
    ) -> None:
        """Handle the approve button interaction."""
        guild = cast(Guild, interaction.guild)
        view = cast("CheckRoleRequestView", self.view)
        view.state = RoleRequestStateEnum.APPROVED
        view.moderator_id = interaction.user.id

        if not guild.me.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to add roles.",
                ),
                ephemeral=True,
            )

        await interaction.response.defer()

        # connect information from components
        for component in interaction.message.components:  # type: ignore
            for item in component.children:  # type: ignore
                if isinstance(item, TextDisplayOverride):  # noqa: SIM102
                    if "User | ID" in item.content:
                        content = item.content
                        content_parts = content.split("\n")
                        view.interaction_user_id = extract_id_from_str(
                            content_parts[0].split("|")[1].strip()
                        )
                        view.interaction_user_nick = (
                            content_parts[1].split(":")[1].strip()
                        )
                        view.role_requested_id = extract_id_from_str(
                            content_parts[2].split(":")[1].strip()
                        )
                        break

        member = await ensure_member_exists(
            guild,
            cast(int, view.interaction_user_id),
        )
        if not member:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Approve failed",
                    "Cannot find this user in guild.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        role = await ensure_role_exists(
            guild, cast(int, view.role_requested_id)
        )
        if not role:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Approve failed",
                    "Cannot find this requested role in the guild.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        async with view.bot.uow.start() as session:
            try:
                last_rr = await get_latest_user_role_request(
                    session,
                    guild_id=guild.id,
                    user_id=cast(int, view.interaction_user_id),
                )
                if not last_rr:
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "Approve failed",
                            "Cannot find this role request in database.",
                            view.bot.user.name,  # type: ignore
                            view.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

                if last_rr.state == RoleRequestStateEnum.APPROVED:
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "Approve failed",
                            "Another moderator approved this request.",
                            view.bot.user.name,  # type: ignore
                            view.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

                last_rr.state = RoleRequestStateEnum.APPROVED
                last_rr.moderator_id = interaction.user.id

                nightcore_notifications_channel_id = (
                    await get_specified_channel(
                        session,
                        guild_id=guild.id,
                        config_type=GuildNotificationsConfig,
                        channel_type=ChannelType.NIGHTCORE_NOTIFICATIONS,
                    )
                )

            except Exception as e:
                logger.exception(
                    "Failed to get role request from %s in %s: %s",
                    view.interaction_user_id,
                    guild.id,
                    e,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Approve failed",
                        "An error occurred while fetching the role request from the database.",  # noqa: E501
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

        try:
            await member.add_roles(role, reason="Role request approved")
        except Exception as e:
            logger.exception(
                "Failed to add role %s to user %s in guild %s: %s",
                role.id,
                member.id,
                guild.id,
                e,
            )
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Approve failed",
                    "An error occurred while adding the role to the user.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        view = view.make_component(disable_all=True)
        await interaction.message.edit(view=view)  # type: ignore

        await interaction.followup.send(
            view=RoleRequestStateView(
                bot=view.bot,
                moderator_id=interaction.user.id,
                user_id=cast(int, view.interaction_user_id),
                role_id=cast(int, view.role_requested_id),
                state=RoleRequestStateEnum.APPROVED,
            )
        )

        await send_role_request_dm(
            moderator_id=interaction.user.id,
            reserve_channel=nightcore_notifications_channel_id,
            user=member,
            state=RoleRequestStateEnum.APPROVED,
        )

        logger.info(
            "Moderator %s requested stats from user %s in guild %s",
            interaction.user.id,
            view.interaction_user_id,
            guild.id,
        )

    @button(
        label="Отклонить запрос",
        custom_id="role_request:decline",
        style=ButtonStyle.grey,
        emoji="<:9349_nope:1414732960841859182>",
    )
    async def decline_role_request(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["CheckRoleRequestView"],
    ) -> None:
        """Handle the decline button interaction."""
        guild = cast(Guild, interaction.guild)
        view = cast("CheckRoleRequestView", self.view)
        view.state = RoleRequestStateEnum.DENIED
        view.moderator_id = interaction.user.id

        if not guild.me.guild_permissions.manage_roles:
            return await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                    "I do not have permission to add roles.",
                ),
                ephemeral=True,
            )

        # connect information from components
        for component in interaction.message.components:  # type: ignore
            for item in component.children:  # type: ignore
                if isinstance(item, TextDisplayOverride):  # noqa: SIM102
                    if "User | ID" in item.content:
                        content = item.content
                        content_parts = content.split("\n")
                        view.interaction_user_id = extract_id_from_str(
                            content_parts[0].split("|")[1].strip()
                        )
                        view.interaction_user_nick = (
                            content_parts[1].split(":")[1].strip()
                        )
                        view.role_requested_id = extract_id_from_str(
                            content_parts[2].split(":")[1].strip()
                        )
                        break

        member = await ensure_member_exists(
            guild,
            cast(int, view.interaction_user_id),
        )
        if not member:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Decline failed",
                    "Cannot find this user in guild.",
                    view.bot.user.name,  # type: ignore
                    view.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        async with view.bot.uow.start() as session:
            try:
                last_rr = await get_latest_user_role_request(
                    session,
                    guild_id=guild.id,
                    user_id=cast(int, view.interaction_user_id),
                )
                if not last_rr:
                    return await interaction.followup.send(
                        embed=ErrorEmbed(
                            "Decline failed",
                            "Cannot find this role request in database.",
                            view.bot.user.name,  # type: ignore
                            view.bot.user.display_avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

                nightcore_notifications_channel_id = (
                    await get_specified_channel(
                        session,
                        guild_id=guild.id,
                        config_type=GuildNotificationsConfig,
                        channel_type=ChannelType.NIGHTCORE_NOTIFICATIONS,
                    )
                )

            except Exception as e:
                logger.exception(
                    "Failed to get role request from %s in %s: %s",
                    view.interaction_user_id,
                    guild.id,
                    e,
                )
                return await interaction.followup.send(
                    embed=ErrorEmbed(
                        "Decline failed",
                        "An error occurred while fetching the role request from the database.",  # noqa: E501
                        view.bot.user.name,  # type: ignore
                        view.bot.user.display_avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

        view = view.make_component(disable_all=True)

        await interaction.response.send_modal(
            DeclineRoleRequestModal(
                bot=view.bot,
                user=member,
                nightcore_notifications_channel_id=nightcore_notifications_channel_id,
                view=view,
                state_view=RoleRequestStateView,
                message=interaction.message,  # type: ignore
            )
        )


# TODO: add attachments
class CheckRoleRequestView(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        interaction_user_id: int | None = None,
        interaction_user_nick: str | None = None,
        role_requested_id: int | None = None,
        moderator_id: int | None = None,
        state: RoleRequestStateEnum | None = None,
        attachments: list[MediaGalleryItem] | None = None,
        all_disabled: bool = False,
    ) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.interaction_user_id = interaction_user_id
        self.role_requested_id = role_requested_id
        self.moderator_id = moderator_id
        self.interaction_user_nick = interaction_user_nick
        self.state = state
        self.attachments = attachments

        self.actions: ManageRoleRequestActionRow

        self.make_component(all_disabled)

    def get_component(self, custom_id: str) -> Item[Self] | None:
        """Get component by custom_id."""
        for item in self.children:
            if isinstance(item, Container):
                for sub_item in item.children:
                    if isinstance(sub_item, ActionRow):
                        for sub_sub_item in sub_item.children:
                            if sub_sub_item.custom_id == custom_id:  # type: ignore
                                return sub_sub_item
                    if isinstance(sub_item, Button):  # noqa: SIM102
                        if sub_item.custom_id == custom_id:
                            return sub_item
            if isinstance(item, Button):  # noqa: SIM102
                if item.custom_id == custom_id:
                    return item
        return None

    def disable_buttons(self):
        """Disable all buttons in the view."""
        if self.actions:
            for item in self.actions.children:
                if isinstance(item, Button):
                    item.disabled = True

    def make_component(self, disable_all: bool = False) -> Self:
        """Create view."""
        self.clear_items()

        container = Container[Self]()

        # header
        container.add_item(TextDisplay[Self]("## Запрос на роль"))
        container.add_item(Separator[Self]())

        # main text
        container.add_item(
            TextDisplay[Self](
                f"**User | ID**: <@{self.interaction_user_id}> | {self.interaction_user_id}\n"  # noqa: E501
                f"**User nickname**: {self.interaction_user_nick}\n"
                f"**Role requested**: <@&{self.role_requested_id}>\n"
            )
        )
        # container.add_item(
        #     TextDisplay[Self](f"User nickname: {self.interaction_user_nick}")
        # )
        # container.add_item(
        #     TextDisplay[Self](f"Role requested: <@&{self.role_requested_id}>")  # noqa: E501
        # )
        container.add_item(Separator[Self]())

        # state
        if self.state:
            state_str = ""
            match self.state:
                case RoleRequestStateEnum.APPROVED:
                    state_str = f"<:15932stars:1421150093960286389> Запрос на статистику был **одобрен** модератором: <@{self.moderator_id}>"  # noqa: E501
                case RoleRequestStateEnum.DENIED:
                    state_str = f"<:21552stars:1421150105981157568> Запрос на статистику был **отклонен** модератором: <@{self.moderator_id}>"  # noqa: E501
                case RoleRequestStateEnum.CANCELED:
                    state_str = "<:21552stars:1421150105981157568> Пользователь отклонил свой запрос на роль."  # noqa: E501
                    self.moderator_id = None
                case RoleRequestStateEnum.EXPIRED:
                    state_str = "<:21552stars:1421150105981157568> Запрос на роль **истек**."  # noqa: E501
                    self.moderator_id = None
                case _:
                    state_str = "Cannot determine state."

            container.add_item(TextDisplay[Self](f"{state_str}"))
            container.add_item(Separator[Self]())

        if self.attachments:
            # attachments
            gallery = MediaGallery[Self](*self.attachments)
            container.add_item(gallery)
            container.add_item(Separator[Self]())

        # manage buttons
        self.actions = ManageRoleRequestActionRow()
        container.add_item(self.actions)
        container.add_item(Separator[Self]())

        if disable_all:
            self.disable_buttons()

        # footer
        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}\n"  # type: ignore
            )
        )

        self.add_item(container)

        return self
