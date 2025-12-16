"""
Transfer view v2 component.

Used for displaying a notification when an item is transferred to a user.
"""

import logging
from datetime import datetime, timezone
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

from src.infra.db.models import GuildEconomyConfig
from src.infra.db.operations import (
    get_specified_field,
    get_user_transfer_history,
)
from src.nightcore.features.economy.utils.pages import (
    build_transfer_history_pages,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts

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
        emoji="<:winterarrowsnightcore:1450562878166925334>",
    )
    async def transfer_history_button(
        self,
        interaction: Interaction["Nightcore"],
        button: Button[LayoutView],
    ):
        """Handle transfer history button callback."""

        bot = interaction.client

        async with bot.uow.start() as session:
            coin_name: str | None = await get_specified_field(
                session,
                guild_id=self.guild_id,
                config_type=GuildEconomyConfig,
                field_name="coin_name",
            )
            transfers = await get_user_transfer_history(
                session, guild_id=self.guild_id, user_id=self.user_id
            )
            logger.info("TRASNFERS: %s", transfers)

        pages = build_transfer_history_pages(transfers, coin_name)

        view = TransferHistoryViewV2(
            bot=bot,
            user_id=self.user_id,
            total_transfers=len(transfers),
            pages=pages,
        )

        await interaction.response.send_message(
            view=view.make_component(),
            ephemeral=True,
        )


class TransferHistoryPaginationActionRow(ActionRow["TransferHistoryViewV2"]):
    def __init__(self):
        super().__init__()

        """Handle transfer history pagination button callback."""

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios1:1442925401696632934>",
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
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios:1442924853085864178>",
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
            accent_color=Color.from_str("#ffffff")
        )  # #515cff

        container.add_item(
            TextDisplay[Self](
                "## <:winterarrowsnightcore:1450562878166925334> История переводов"  # noqa: E501
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

        now = datetime.now(timezone.utc)

        container.add_item(
            TextDisplay[Self](
                f"-# Page {self.current_page + 1} of {len(self.pages)}\n"
                f"-# Powered by {self.bot.user.name} in {discord_ts(now)}"  # type: ignore
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

        container = Container[Self](accent_color=Color.from_str("#515cff"))

        container.add_item(
            TextDisplay[Self](
                "### <:arrows:1442916548921790575> Уведомление о переводе"
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                f"Пользователь <@{user_id}> перевел вам {amount} {item_name}\n"
            )
        )
        if comment:
            container.add_item(
                TextDisplay[Self](
                    f'<:send:1442916328641134632> **Комментарий:** \n> *"{comment}"*'  # noqa: E501
                )
            )
        container.add_item(Separator[Self]())

        now = datetime.now(timezone.utc)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
