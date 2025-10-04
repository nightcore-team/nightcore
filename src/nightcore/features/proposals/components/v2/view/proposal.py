import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Color, Guild, Member, Message
from discord.interactions import Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.infra.db.operations import get_moderation_access_roles
from src.nightcore.components.embed import MissingPermissionsEmbed
from src.nightcore.exceptions import FieldNotConfiguredError
from src.nightcore.features.proposals.components.modal import (
    CheckProposalModal,
)
from src.nightcore.features.tickets.utils import extract_id_from_str
from src.nightcore.utils import discord_ts, has_any_role_from_sequence

logger = logging.getLogger(__name__)


class ManageProposalActionRow(ActionRow["ProposalViewV2"]):
    def __init__(self):
        super().__init__()

    @button(
        label="Одобрить",
        custom_id="proposal:approve",
        style=ButtonStyle.grey,
        emoji="<:52104checkmark:1414732973005340672>",
    )
    async def approve_proposal(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["ProposalViewV2"],
    ) -> None:
        """Approve proposal."""
        guild = cast(Guild, interaction.guild)
        view = cast("ProposalViewV2", self.view)
        view.moderator_id = interaction.user.id
        message = cast(Message, interaction.message)

        async with view.bot.uow.start() as session:
            if not (
                moderation_access_roles := await get_moderation_access_roles(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("moderation access")

        has_moder_role = has_any_role_from_sequence(
            cast(Member, interaction.user), moderation_access_roles
        )
        if not has_moder_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        for container in interaction.message.components:  # type: ignore
            for item in container.children:  # type: ignore
                if isinstance(item, TextDisplay):
                    if item.id == 2:
                        view.proposals_count = extract_id_from_str(
                            item.content
                        )
                    if item.id == 4:
                        view.user_id = extract_id_from_str(item.content)

                    if item.id == 5:
                        view.description = item.content.replace("```", "")

        updated_view = ProposalViewV2(
            bot=view.bot,
            proposals_count=view.proposals_count,
            description=view.description,
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
        emoji="<:9349_nope:1414732960841859182>",
    )
    async def decline_proposal(
        self,
        interaction: Interaction["Nightcore"],
        button: Button["ProposalViewV2"],
    ) -> None:
        """Decline proposal."""
        guild = cast(Guild, interaction.guild)
        view = cast("ProposalViewV2", self.view)
        view.moderator_id = interaction.user.id
        message = cast(Message, interaction.message)

        async with view.bot.uow.start() as session:
            if not (
                moderation_access_roles := await get_moderation_access_roles(
                    session, guild_id=guild.id
                )
            ):
                raise FieldNotConfiguredError("moderation access")

        has_moder_role = has_any_role_from_sequence(
            cast(Member, interaction.user), moderation_access_roles
        )
        if not has_moder_role:
            return await interaction.response.send_message(
                embed=MissingPermissionsEmbed(
                    self.bot.user.name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        for container in interaction.message.components:  # type: ignore
            for item in container.children:  # type: ignore
                if isinstance(item, TextDisplay):
                    if item.id == 2:
                        view.proposals_count = extract_id_from_str(
                            item.content
                        )
                    if item.id == 4:
                        view.user_id = extract_id_from_str(item.content)

                    if item.id == 5:
                        view.description = item.content.replace("```", "")

        updated_view = ProposalViewV2(
            bot=view.bot,
            proposals_count=view.proposals_count,
            description=view.description,
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
    ):
        super().__init__(timeout=None)

        self.bot = bot
        self.proposals_count = proposals_count
        self.description = description
        self.user_id = user_id
        self.status = status or "На рассмотрении"  # noqa: RUF001
        self.answer = answer
        self.moderator_id = moderator_id
        self.color = color

    def _disable_buttons(self):
        for item in self.children:
            if isinstance(item, ManageProposalActionRow):
                for button in item.children:
                    if isinstance(button, Button):
                        button.disabled = True

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
                f"Автор предложения: <@{self.user_id}>\nСтатус: **{self.status}**"  # noqa: E501, RUF001
            )
        )
        container.add_item(TextDisplay[Self](f"```{self.description}```"))
        container.add_item(Separator[Self]())

        if self.answer:
            container.add_item(
                TextDisplay[Self](f"### Ответ от: <@{self.moderator_id}>\n")
            )
            container.add_item(TextDisplay[Self](f"```{self.answer}```"))
            container.add_item(Separator[Self]())

        container.add_item(ManageProposalActionRow())
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        if disable_all:
            self._disable_buttons()

        self.add_item(container)

        return self
