import logging
from typing import TYPE_CHECKING, Self, cast

import discord
from discord.ui import Modal, TextInput

from src.config.config import config

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

            additional_view = None
            self.view.moderator_id = interaction.user.id
            if (
                len(cast(str, self.view.description)) + len(reason)
                >= config.bot.VIEW_V2_DESCRIPTION_LIMIT
            ):
                from src.nightcore.features.proposals.components.v2.view import (  # noqa: E501
                    AdditionalProposalAnswerViewV2,
                )

                additional_view = AdditionalProposalAnswerViewV2(
                    bot=self.bot,
                    proposal_message_link=self.message.jump_url,
                    description=reason,
                    moderator_id=interaction.user.id,
                    color=self.view.color,
                )
                self.view.answer = "Ответ слишком длинный, поэтому он был добавлен в виде отдельного эмбеда."  # noqa: E501
            else:
                self.view.answer = reason

            view = self.view.make_component(disable_all=True)

            message = await self.message.edit(view=view)
            if additional_view:
                await message.reply(view=additional_view)

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
