"""Command to check days until winter holidays."""

from __future__ import annotations

from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext.commands import Cog  # type: ignore
from discord.interactions import Interaction

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.components.embed import ErrorEmbed
from src.nightcore.features.meta.components.v2.view.winter_holidays import (
    WinterHolidaysViewV2,
)
from src.nightcore.features.meta.utils.winter_holidays import (
    get_all_holidays,
    parse_timezone,
)
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)


class WinterHolidays(Cog):
    def __init__(self, bot: Nightcore) -> None:
        self.bot = bot

    @app_commands.command(
        name="winter_holidays", description="Зима в сердцах наших ;)"
    )  # type: ignore
    @app_commands.describe(
        calendar="Выберите календарь (Григорианский или Юлианский)",
        timezone="Ваш часовой пояс",
    )
    @app_commands.choices(
        calendar=[
            app_commands.Choice(name="Григорианский", value="gregorian"),
            app_commands.Choice(name="Юлианский", value="julian"),
        ]
    )
    @check_required_permissions(PermissionsFlagEnum.NONE)  # type: ignore
    async def winter_holidays(
        self,
        interaction: Interaction[Nightcore],
        calendar: str = "gregorian",
        timezone: str = "UTC",
        ephemeral: bool = True,
    ):
        """Send a message displaying the bot's current latency."""

        await interaction.response.defer(ephemeral=ephemeral, thinking=True)

        # try to parse timezone
        zone_info = parse_timezone(timezone)
        if zone_info is None:
            return await interaction.followup.send(
                embed=ErrorEmbed(
                    "Ошибка часового пояса",
                    "Не удалось распознать указанный часовой пояс.",
                    self.bot.user.display_name,  # type: ignore
                    self.bot.user.display_avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        # calculate days until winter holidays based on calendar and timezone
        holidays = get_all_holidays(zone_info, calendar)

        # get random winter holiday image or load from cache
        # image_url = await self.bot.photo_cache.get_or_fetch(
        #     key="winter_holidays",
        #     fetch_fn=lambda: self.bot.apis.unsplash.get_random_photo(
        #         query="christmas new year winter holidays"
        #     ),
        # )

        # send layout view with results
        view = WinterHolidaysViewV2(
            bot=self.bot,
            calendar=calendar,
            tz=zone_info.key,
            holidays=holidays,
        )

        await interaction.followup.send(view=view)


async def setup(bot: Nightcore):
    """Setup the WinterHolidays cog."""
    await bot.add_cog(WinterHolidays(bot))
