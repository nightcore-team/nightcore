"""Proposal view v2 component."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Color, Message, app_commands
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    Item,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import MissingPermissionsEmbed
from src.nightcore.features.proposals.components.modal import (
    CheckProposalModal,
)
from src.nightcore.features.tickets.utils import extract_id_from_str
from src.nightcore.utils import discord_ts
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

logger = logging.getLogger(__name__)


class ManageProposalActionRow(ActionRow["ProposalViewV2"]):
    def __init__(self):
        super().__init__()

    @button(
        label="Одобрить",
        custom_id="proposal:approve",
        style=ButtonStyle.grey,
        emoji="<:check:1442915033079353404>",
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.HEAD_MODERATION_ACCESS)  # type: ignore
    async def approve_proposal(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["ProposalViewV2"],
    ) -> None:
        """Approve proposal."""

        view = cast("ProposalViewV2", self.view)
        view.moderator_id = interaction.user.id
        message = cast(Message, interaction.message)

        for container in interaction.message.components:  # type: ignore
            for item in container.children:  # type: ignore
                if item.id == 2:  # type: ignore
                    view.proposals_count = extract_id_from_str(item.content)  # type: ignore
                if item.id == 4:  # type: ignore
                    view.user_id = extract_id_from_str(item.content)  # type: ignore

                if item.id == 5:  # type: ignore
                    view.description = item.content.replace("```", "")  # type: ignore

        updated_view = ProposalViewV2(
            bot=view.bot,
            proposals_count=view.proposals_count,
            description=view.description,  # type: ignore
            user_id=view.user_id,
            status="Одобрено",
            color=Color.green(),
        )

        # send modal
        modal = CheckProposalModal(
            bot=view.bot,
            view=updated_view,
            message=message,
        )
        await interaction.response.send_modal(modal)

    @button(
        label="Отклонить",
        custom_id="proposal:decline",
        style=ButtonStyle.grey,
        emoji="<:failed:1442915170320912506>",
    )  # type: ignore
    @check_required_permissions(PermissionsFlagEnum.HEAD_MODERATION_ACCESS)  # type: ignore
    async def decline_proposal(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["ProposalViewV2"],
    ) -> None:
        """Decline proposal."""

        view = cast("ProposalViewV2", self.view)
        view.moderator_id = interaction.user.id
        message = cast(Message, interaction.message)

        for container in interaction.message.components:  # type: ignore
            for item in container.children:  # type: ignore
                if item.id == 2:  # type: ignore
                    view.proposals_count = extract_id_from_str(item.content)  # type: ignore
                if item.id == 4:  # type: ignore
                    view.user_id = extract_id_from_str(item.content)  # type: ignore

                if item.id == 5:  # type: ignore
                    view.description = item.content.replace("```", "")  # type: ignore

        updated_view = ProposalViewV2(
            bot=view.bot,
            proposals_count=view.proposals_count,
            description=view.description,  # type: ignore
            user_id=view.user_id,
            status="Отклонено",
            color=Color.red(),
        )
        # send modal
        modal = CheckProposalModal(
            bot=view.bot,
            view=updated_view,
            message=message,
        )
        await interaction.response.send_modal(modal)


class ProposalViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        proposals_count: int | None = None,
        description: str | None = None,
        user_id: int | None = None,
        status: str | None = None,
        moderator_id: int | None = None,
        answer: str | None = None,
        color: Color | None = None,
        _build: bool = False,
    ):
        super().__init__(timeout=None)

        self.bot = bot
        self.proposals_count = proposals_count
        self.description = description
        self.user_id = user_id
        self.status = status or "На рассмотрении"
        self.answer = answer
        self.moderator_id = moderator_id
        self.color = color

        self.actions = ManageProposalActionRow()

        if _build:
            self.make_component()

    def _disable_buttons(self):
        if self.actions:
            for item in self.actions.children:
                if isinstance(item, Button):
                    item.disabled = True  # type: ignore

    def make_component(self, disable_all: bool = False) -> Self:
        """Create view."""

        self.clear_items()

        container = Container[Self](accent_color=self.color)

        container.add_item(
            TextDisplay[Self](f"## Предложение #{self.proposals_count}")
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"Автор предложения: <@{self.user_id}>\nСтатус: **{self.status}**"  # noqa: E501
            )
        )
        container.add_item(TextDisplay[Self](f"{self.description}"))
        container.add_item(Separator[Self]())

        if self.answer:
            container.add_item(
                TextDisplay[Self](f"### Ответ от: <@{self.moderator_id}>\n")
            )
            container.add_item(TextDisplay[Self](f"{self.answer}"))
            container.add_item(Separator[Self]())

        container.add_item(self.actions)
        container.add_item(Separator[Self]())

        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        if disable_all:
            self._disable_buttons()

        self.add_item(container)

        return self

    async def on_error(
        self,
        interaction: Interaction,
        error: Exception,
        item: Item[Self],
    ):
        """Handle errors for button interactions."""
        original = getattr(error, "original", error)

        if not isinstance(original, app_commands.MissingPermissions):
            return

        missing_perms: list[str] = getattr(original, "missing_permissions", [])

        _missing_perms = ", ".join(missing_perms)

        if not interaction.response.is_done():
            await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    interaction.client.user.name,  # type: ignore
                    interaction.client.user.display_avatar.url,  # type: ignore
                    f"Вам не хватает следующих прав для использования этой команды: {_missing_perms}.",  # noqa: E501
                ),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                embed=MissingPermissionsEmbed(
                    interaction.client.user.name,  # type: ignore
                    interaction.client.user.display_avatar.url,  # type: ignore
                    f"Вам не хватает следующих прав для использования этой команды: {missing_perms}.",  # noqa: E501
                ),
                ephemeral=True,
            )


class AdditionalProposalAnswerViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        moderator_id: int,
        description: str,
        proposal_message_link: str,
        color: Color | None = None,
    ):
        super().__init__(timeout=None)

        container = Container[Self](accent_color=color)

        container.add_item(
            TextDisplay[Self](
                f"## Дополнение к предложению: {proposal_message_link}"
            )
        )
        container.add_item(Separator[Self]())
        container.add_item(
            TextDisplay[Self](f"### Ответ от: <@{moderator_id}>\n")
        )
        container.add_item(TextDisplay[Self](f"{description}"))
        container.add_item(Separator[Self]())

        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
