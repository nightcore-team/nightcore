"""Role members view v2 component."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Self

import discord
from discord import ButtonStyle, Color, MediaGalleryItem
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    MediaGallery,
    Section,
    Separator,
    TextDisplay,
    Thumbnail,
)

from src.nightcore.utils import discord_ts

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore


class AboutViewV2(LayoutView):
    def __init__(
        self,
        bot: Nightcore,
        total_members: int,
        created_at: datetime,
        memory_usage: str,
        uptime: str,
    ) -> None:
        super().__init__(timeout=30)

        container = Container[Self](accent_color=Color.from_str("#515cff"))

        container.add_item(
            # Section[Self](
            TextDisplay[Self](
                "## <:nightcore:1437888715849728041> Nightcore\n\n"
                # "**Разработчик: <@566255833684508672>**\n"
                "> *Born from the rhythm of the night, crafted in the pulse of the stars.*"  # noqa: E501
            ),
            #     accessory=Thumbnail[Self](
            #         # bot.user.display_avatar.url  # type: ignore
            #         "https://cdn.discordapp.com/attachments/735890305844510762/1437951359155437698/q0XkV8j.png?ex=69151c0f&is=6913ca8f&hm=7b0ad8c06bd7ca98da7b8050892b78843bf49e8fa275e8ace5318bbf58ed4162&"
            #     ),  # type: ignore
            # )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            TextDisplay[Self](
                "## <:shootingstar:1437888733990097057> Информация о боте\n\n"
                f"> **Бот ID**: `{bot.user.id}`\n"  # type: ignore
                f"> **Задержка**: `{bot.latency * 1000:.2f} ms`\n"
                f"> **Дата создания: {discord_ts(created_at)}**\n"
                f"> **Количество серверов: `{len(bot.guilds)}`**\n"
                f"> **Количество пользователей: `{total_members}`**\n"
            )
        )
        container.add_item(Separator[Self]())
        container.add_item(
            TextDisplay[Self](
                "## <:code:1437955860251803680> Техническая информация\n\n"
                f"> **Потребление памяти: `{memory_usage}`**\n"
                f"> **Библиотека: `discord.py v{getattr(discord, '__version__', 'unknown')}`**\n"  # noqa: E501
                f"> **Время работы: {uptime}**\n"
            )
        )
        container.add_item(Separator[Self]())

        container.add_item(
            ActionRow[Self](
                Button[Self](
                    style=ButtonStyle.link,
                    label="Nightcore Community",
                    emoji="<:shootingstar:1437888733990097057>",
                    url="https://discord.gg/sSZs2sWhUZ",
                ),
                Button[Self](
                    style=ButtonStyle.gray,
                    label="Bug Report",
                    emoji="<:3052shinybluebughunter:1437948101263360053>",
                    custom_id="nightcore:bug_report",
                ),
            )
        )
        container.add_item(Separator[Self]())

        # container.add_item(
        #     MediaGallery[Self](
        #         MediaGalleryItem(
        #             "https://images-ext-1.discordapp.net/external/e_SYSWxGGdr26MaQCJu7jxyKy8DhqGjyuxJNFYZp5_g/%3Fsize%3D512/https/cdn.discordapp.com/banners/1038884944816119868/fb490c2f1dd3698a6a651532e2eb95fb.png?format=webp&quality=lossless&width=614&height=373"
        #         )
        #     )
        # )
        # container.add_item(Separator[Self]())

        now = discord.utils.utcnow()
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
