"""
Transfer view v2 component.

Used for displaying a notification when an item is transferred to a user.
"""

import logging
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, Color
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

logger = logging.getLogger(__name__)


class TransferHistoryActionRow(ActionRow[LayoutView]):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__()

        self.guild_id = guild_id
        self.user_id = user_id

    @button(
        style=ButtonStyle.grey,
        label="История переводов",
        custom_id="balance:history",
        emoji="<:nightcoreArrowsLeftRight:1540432969431519277>",
    )
    async def transfer_history_button(
        self,
        interaction: Interaction["Nightcore"],
        button: Button[LayoutView],
    ):
        """Handle transfer history button callback."""

        from .profile.handlers.transfer import open_transfer_history

        await open_transfer_history(
            interaction,
            guild_id=self.guild_id,
            user_id=self.user_id,
        )


class TransferHistoryPaginationActionRow(ActionRow["TransferHistoryViewV2"]):
    def __init__(self):
        super().__init__()

        """Handle transfer history pagination button callback."""

    @button(
        style=ButtonStyle.grey,
        emoji="<:nightcoreArrowLeftCyan:1540434220436951172>",
        custom_id="balance:history:prev",
    )
    async def previous(
        self, interaction: Interaction, button: Button["TransferHistoryViewV2"]
    ):
        """Go to the previous page."""
        view = cast(TransferHistoryViewV2, self.view)

        if view.current_page > 0:
            view.current_page -= 1
        await interaction.response.edit_message(
            view=view.make_component(),
        )

    @button(
        style=ButtonStyle.grey,
        emoji="<:nightcoreArrowRightCyan:1540434390780477551>",
        custom_id="balance:history:next",
    )
    async def next(
        self, interaction: Interaction, button: Button["TransferHistoryViewV2"]
    ):
        """Go to the next page."""
        view = cast(TransferHistoryViewV2, self.view)
        if view.current_page < len(view.pages) - 1:  # type: ignore
            view.current_page += 1  # type: ignore
        await interaction.response.edit_message(
            view=view.make_component(),  # type: ignore
        )


class TransferHistoryViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_id: int,
        total_transfers: int,
        pages: list[str],
    ):
        super().__init__(timeout=None)

        self.bot = bot
        self.user_id = user_id
        self.total_transfers = total_transfers
        self.pages = pages
        self.current_page = 0

        self.pagination: TransferHistoryPaginationActionRow

    def _update_buttons(self):
        if not self.pagination:
            return

        for child in self.pagination.children:
            if isinstance(child, Button):
                if child.custom_id == "balance:history:prev":
                    child.disabled = self.current_page == 0  # type: ignore
                elif child.custom_id == "balance:history:next":
                    child.disabled = self.current_page == len(self.pages) - 1  # type: ignore

    def make_component(self) -> Self:
        """Create a new component for the current page."""

        self.clear_items()

        container = Container[Self](
            accent_color=Color.from_str("#5EC9B3")
        )  # #515cff

        container.add_item(
            TextDisplay[Self](
                "### <:nightcoreArrowsLeftRight:1540432969431519277> История переводов"  # noqa: E501
            )
        )
        container.add_item(
            TextDisplay[Self](
                f"\n**Общее количество переводов:** {self.total_transfers}"
            )
        )
        container.add_item(Separator[Self]())

        self.pagination = TransferHistoryPaginationActionRow()

        if len(self.pages) > 1:
            container.add_item(
                TextDisplay[Self](self.pages[self.current_page])
            )
            container.add_item(Separator[Self]())
            self.add_item(self.pagination)
        else:
            container.add_item(TextDisplay[Self](self.pages[0]))
            container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"-# Page {self.current_page + 1} of {len(self.pages)}"
            )
        )

        self.add_item(container)

        return self


class TransferCoinsViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_id: int,
        item_name: str,
        amount: int,
        comment: str | None = None,
    ):
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(TextDisplay[Self]("### Уведомление о переводе\n"))
        container.add_item(
            TextDisplay[Self](
                f"Пользователь <@{user_id}> перевел вам {amount} {item_name} <:nightcoreBanknoteUp:1540436249809133683>\n"  # noqa: E501
            )
        )
        if comment:
            container.add_item(Separator())
            container.add_item(
                TextDisplay[Self](
                    f'<:nightcoreComment:1540436103562006548> **Комментарий:** \n> *"{comment}"*'  # noqa: E501
                )
            )

        self.add_item(container)
