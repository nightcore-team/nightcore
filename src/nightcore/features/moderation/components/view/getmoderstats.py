"""View for paginating infractions."""

from datetime import datetime
from typing import TYPE_CHECKING, Self, cast

from discord import ButtonStyle, ClientUser
from discord.colour import Color
from discord.embeds import Embed
from discord.interactions import Interaction
from discord.ui import Button, View, button

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class GetModerationStatsView(View):
    def __init__(
        self,
        author_id: int,
        pages: list[list[dict[int, dict[str, str]]]],
        from_date: datetime,
        to_date: datetime,
        bot: "Nightcore",
        timeout: int = 180,
    ):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.pages = pages
        self.current_page = 0
        self.bot = bot
        self.from_date = from_date
        self.to_date = to_date

        self._embed: Embed | None = None
        self._update_buttons()

    def _update_buttons(self):
        for child in self.children:
            if isinstance(child, Button):
                if child.custom_id == "infractions_prev":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "infractions_next":
                    child.disabled = self.current_page == len(self.pages) - 1

    def _make_embed(self) -> Embed:
        page = self.pages[self.current_page]
        if self._embed:
            self._embed.clear_fields()

            for p in page:
                for v in p.values():
                    self._embed.add_field(
                        name=v.get("nickname"),
                        value=v.get("stats"),
                        inline=True,
                    )

            return self._embed

        self._embed = Embed(
            title=f"Moderation stats from {self.from_date.date()} to {self.to_date.date()}",  # noqa: E501
            color=Color.blurple(),
        )
        for p in page:
            for k, v in p.items():
                self._embed.add_field(name=f"<@{k}>", value=v, inline=True)
        self._embed.set_footer(
            text=f"Page {self.current_page + 1} / {len(self.pages)}",
            icon_url=cast(ClientUser, self.bot.user).display_avatar.url,
        )
        return self._embed

    async def interaction_check(
        self,
        interaction: Interaction,
    ) -> bool:
        """Ensure that only the author can interact with the view."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "You can't manage this pagination.", ephemeral=True
            )
            return False
        return True

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios1:1409851002256887808>",
        custom_id="infractions_prev",
    )
    async def previous(self, interaction: Interaction, button: Button[Self]):
        """Go to previous page."""
        self.current_page -= 1
        self._update_buttons()
        await interaction.response.edit_message(
            embed=self._make_embed(), view=self
        )

    @button(
        style=ButtonStyle.secondary,
        emoji="<:41036arrowforwardios:1409850992593338460>",
        custom_id="infractions_next",
    )
    async def next(self, interaction: Interaction, button: Button[Self]):
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
                child.disabled = True
