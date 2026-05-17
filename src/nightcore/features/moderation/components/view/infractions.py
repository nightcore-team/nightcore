"""View for paginating infractions."""

from typing import TYPE_CHECKING

from discord import ButtonStyle, User
from discord.colour import Color
from discord.embeds import Embed
from discord.interactions import Interaction
from discord.ui import Button, View, button

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class InfractionsView(View):
    def __init__(
        self,
        author_id: int,
        pages: list[str],
        user: User,
        bot: "Nightcore",
    ):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.pages = pages
        self.current_page = 0
        self.user = user
        self.bot = bot

        self._update_buttons()

    def _update_buttons(self):
        for child in self.children:
            if isinstance(child, Button):
                if child.custom_id == "infractions:prev":
                    child.disabled = self.current_page == 0  # type: ignore
                elif child.custom_id == "infractions:next":
                    child.disabled = self.current_page == len(self.pages) - 1  # type: ignore

    def _make_embed(self) -> Embed:
        embed = Embed(
            description=self.pages[self.current_page],
            color=Color.blurple(),
        )
        embed.set_author(
            name=f"{self.user} ➤ Список нарушений",
            icon_url=self.user.display_avatar.url,
        )
        embed.set_footer(
            text=f"Page {self.current_page + 1} / {len(self.pages)}",
            icon_url=self.bot.user.display_avatar.url,
        )
        return embed

    async def interaction_check(
        self,
        interaction: Interaction,
    ) -> bool:
        """Ensure that only the author can interact with the view."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Вы не можете управлять этой пагинацией.", ephemeral=True
            )
            return False
        return True

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios1:1442925401696632934>",
        custom_id="infractions:prev",
    )
    async def previous(
        self, interaction: Interaction, button: Button["InfractionsView"]
    ):
        """Go to previous page."""
        self.current_page -= 1
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self._make_embed(), view=self
        )

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios:1442924853085864178>",
        custom_id="infractions:next",
    )
    async def next(
        self, interaction: Interaction, button: Button["InfractionsView"]
    ):
        """Go to next page."""
        self.current_page += 1
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self._make_embed(), view=self
        )

    async def on_timeout(self):
        """Disable all buttons when view times out."""
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True  # type: ignore
