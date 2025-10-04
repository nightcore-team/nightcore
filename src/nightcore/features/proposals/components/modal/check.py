import logging
from typing import TYPE_CHECKING, Self

import discord
from discord.ui import Modal, TextInput

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore
    from src.nightcore.features.proposals.components.v2.view import (
        ProposalViewV2,
    )

logger = logging.getLogger(__name__)


class CheckProposalModal(Modal, title="Рассмотрение предложения"):
    reason = TextInput[Self](
        label="Причина",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000,
    )

    def __init__(
        self,
        bot: "Nightcore",
        view: "ProposalViewV2",
        message: discord.Message,
    ):
        super().__init__()

        self.bot = bot
        self.view = view
        self.message = message

    # TODO: fix it and fix lenght of answer for changing embed
    async def on_submit(self, interaction: discord.Interaction):
        """Handles the submission of the ban form modal."""
        try:
            reason = self.reason.value

            self.view.moderator_id = interaction.user.id
            self.view.answer = reason

            view = self.view.make_component(disable_all=True)

            await self.message.edit(view=view)
        except Exception as e:
            logger.exception(
                "Error handling proposal check modal submission: %s", e
            )
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Произошла ошибка при обработке вашего запроса.",
                    ephemeral=True,
                )

        await interaction.response.send_message(
            "Ваш ответ был записан.", ephemeral=True
        )
