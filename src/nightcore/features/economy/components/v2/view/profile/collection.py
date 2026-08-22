"""
User collection views v2 component.

Used for displaying a user's cases, colors, and opening related views.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from discord import ButtonStyle, Color, Interaction
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Separator,
    TextDisplay,
    button,
)

from src.infra.db.operations import get_or_create_user
from src.nightcore.utils import discord_ts

from .handlers.transfer import open_transfer_history

if TYPE_CHECKING:
    from src.infra.db.models.color import Color as UserColor
    from src.infra.db.models.user import UserCase
    from src.nightcore.bot import Nightcore


class CasesCollectionViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_id: int,
        cases: list["UserCase"],
    ):
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(
            TextDisplay[Self](
                "### <:nightcoreCase:1540678039841673216> Кейсы: "
            )
        )
        container.add_item(Separator[Self]())

        if len(cases) > 0:
            container.add_item(
                TextDisplay[Self](
                    "\n".join(
                        f"> {case.item.name}, количество: {case.amount}"
                        for case in cases
                    )
                )
            )
        else:
            container.add_item(
                TextDisplay[Self]("> У пользователя пока нет кейсов.")
            )
        container.add_item(Separator[Self]())

        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)


class ColorsCollectionViewV2(LayoutView):
    def __init__(
        self,
        bot: "Nightcore",
        user_id: int,
        colors: list["UserColor"],
    ):
        super().__init__(timeout=None)

        container = Container[Self](accent_color=Color.from_str("#5EC9B3"))

        container.add_item(
            TextDisplay[Self](
                "### <:nightcoreColor:1540678362970988544> Цвета: "
            )
        )
        container.add_item(Separator[Self]())

        if len(colors) > 0:
            container.add_item(
                TextDisplay[Self](
                    "\n".join(f"> <@&{color.role_id}>" for color in colors)
                )
            )
        else:
            container.add_item(
                TextDisplay[Self]("> У пользователя пока нет цветов.")
            )
        container.add_item(Separator[Self]())

        now = datetime.now(UTC)

        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)


class UserProfileActionRow(ActionRow[LayoutView]):
    def __init__(
        self,
        bot: "Nightcore",
        guild_id: int,
        user_id: int,
    ):
        super().__init__()

        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id

    @button(
        style=ButtonStyle.grey,
        label="История переводов",
        custom_id="profile:history",
        emoji="<:nightcoreArrowsLeftRight:1540432969431519277>",
    )
    async def transfer_history_button(
        self,
        interaction: Interaction["Nightcore"],
        button: Button[LayoutView],
    ):
        """Handle transfer history button callback."""

        await open_transfer_history(
            interaction,
            guild_id=self.guild_id,
            user_id=self.user_id,
        )

    @button(
        style=ButtonStyle.grey,
        label="Цвета",
        custom_id="profile:colors",
        emoji="<:nightcoreColor:1540678362970988544>",
    )
    async def colors_button(
        self,
        interaction: Interaction["Nightcore"],
        button: Button[LayoutView],
    ):
        """Handle colors collection button callback."""

        async with self.bot.uow.start() as session:
            user_record, _ = await get_or_create_user(
                session,
                guild_id=self.guild_id,
                user_id=self.user_id,
                with_relations=True,
            )
            colors: list[UserColor] = user_record.colors

        view = ColorsCollectionViewV2(
            bot=self.bot,
            user_id=self.user_id,
            colors=colors,
        )

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )

    @button(
        style=ButtonStyle.grey,
        label="Кейсы",
        custom_id="profile:cases",
        emoji="<:nightcoreCase:1540678039841673216>",
    )
    async def cases_button(
        self,
        interaction: Interaction["Nightcore"],
        button: Button[LayoutView],
    ):
        """Handle cases collection button callback."""

        async with self.bot.uow.start() as session:
            user_record, _ = await get_or_create_user(
                session,
                guild_id=self.guild_id,
                user_id=self.user_id,
                with_relations=True,
            )
            cases: list[UserCase] = user_record.cases

        view = CasesCollectionViewV2(
            bot=self.bot,
            user_id=self.user_id,
            cases=cases,
        )

        await interaction.response.send_message(
            view=view,
            ephemeral=True,
        )
