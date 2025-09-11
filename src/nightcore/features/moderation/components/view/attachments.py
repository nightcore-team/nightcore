"""Attachments collector view for ban requests."""

import asyncio
from typing import Self

from discord import ButtonStyle
from discord.interactions import Interaction
from discord.ui import Button, View, button


class AttachmentsCollectorView(View):
    def __init__(self, author_id: int):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.done = asyncio.Event()
        self.cancelled = False

    # TODO: add disabling buttons after done/cancelled/timeout
    @button(
        style=ButtonStyle.green,
        emoji="<:52104checkmark:1414732973005340672>",
        label="Done",
        custom_id="done_attachments_collector",
    )
    async def done_button(
        self, interaction: Interaction, button: Button[Self]
    ):
        """Mark the collection as done."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "You can't use this button.", ephemeral=True
            )
            return
        if not self.done.is_set():
            self.done.set()

        await interaction.response.defer()  # просто ACK

    @button(
        style=ButtonStyle.red,
        emoji="<:9349_nope:1414732960841859182>",
        label="Cancel",
        custom_id="cancel_attachments_collector",
    )
    async def cancel_button(
        self, interaction: Interaction, button: Button[Self]
    ):
        """Cancel the collection."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "You can't use this button.", ephemeral=True
            )
            return
        if not self.done.is_set():
            self.cancelled = True
            self.done.set()

        await interaction.response.defer()
