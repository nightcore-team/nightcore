"""Private rooms log embed component."""

from datetime import UTC, datetime

import discord
from discord.embeds import Embed

from src.nightcore.bot import Nightcore


class PrivateRoomLogEmbed(Embed):
    def __init__(
        self,
        title: str,
        user_id: int,
        bot: Nightcore,
        channel: discord.VoiceChannel,
    ):
        super().__init__(
            title=title,
            color=discord.Color.blurple(),
            timestamp=datetime.now(UTC),
        )
        self.set_footer(
            text="Powered by nightcore",
            icon_url=bot.user.display_avatar.url,  # type: ignore
        )

        self.add_field(name="Пользователь", value=f"<@{user_id}> ({user_id})")
        self.add_field(name="Канал", value=f"<#{channel.id}> ({channel.id})")
        self.add_field(name="Имя канала", value=channel.name)
