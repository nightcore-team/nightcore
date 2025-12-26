"""Roles selector view v2 component."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from discord import Color, MediaGalleryItem, Role, SelectOption
from discord.ui import (
    ActionRow,
    Container,
    LayoutView,
    MediaGallery,
    Select,
    Separator,
    TextDisplay,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.utils import discord_ts


class RoleSelectorSelect(Select["RoleSelectorViewV2"]):
    def __init__(self, options: list[SelectOption]) -> None:
        super().__init__(
            placeholder="Выберите роли",
            options=options,
            custom_id="role_selector:select_roles",
        )


class RoleSelectorViewV2(LayoutView):
    def __init__(
        self,
        bot: Nightcore,
        roles: list[Role],
        title: str | None = None,
        description: str | None = None,
        image_url: str | None = None,
        color: Color | None = None,
    ) -> None:
        super().__init__(timeout=None)

        container = Container[Self](accent_color=color)

        if title:
            container.add_item(TextDisplay[Self](f"## {title}"))
            container.add_item(Separator[Self]())

        if description:
            container.add_item(TextDisplay[Self](description))
            container.add_item(Separator[Self]())

        if image_url:
            container.add_item(MediaGallery[Self](MediaGalleryItem(image_url)))
            container.add_item(Separator[Self]())

        options = [
            *[
                SelectOption(label=role.name, value=str(role.id))
                for role in roles
            ],
            SelectOption(label="Удалить все роли", value="remove_all_roles"),
        ]
        container.add_item(ActionRow(RoleSelectorSelect(options)))
        container.add_item(Separator[Self]())

        now = datetime.now(UTC)
        container.add_item(
            TextDisplay[Self](
                f"-# Powered by {bot.user.name} in {discord_ts(now)}"  # type: ignore
            )
        )

        self.add_item(container)
