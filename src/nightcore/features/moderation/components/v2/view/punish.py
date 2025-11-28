"""
Punish view v2 component.

Used for displaying punishment information in guilds.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Self

from discord import Color, Member, User
from discord.ui import (
    Container,
    LayoutView,
    Separator,
    TextDisplay,
)

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

from src.nightcore.features.moderation.utils.punishments import (
    PUNISHMENTS_DESC_DICT,
)
from src.nightcore.utils import discord_ts


class PunishViewV2(LayoutView):
    """View for punishment notifications.

    Supports 3 modes:
    - server: Notification in server (3rd person)
    - dm: Notification in user's DM (2nd person)
    - expired: Notification when punishment expired (2nd person)
    """

    def __init__(
        self,
        bot: Nightcore,
        user: Member | User,
        punish_type: str,
        moderator_id: int,
        reason: str,
        *,
        guild_name: str | None = None,
        mode: str = "server",  # "server" | "dm" | "expired"
        duration: str | None = None,
    ):
        super().__init__()

        container = Container[Self](accent_color=Color.from_str("#9300d2"))

        if mode == "expired":
            title = "Оповещение об окончании наказания"
        elif "un" in punish_type:
            title = "Оповещение о снятии наказания"
        else:
            title = "Оповещение о выдаче наказания"

        if mode == "expired":
            main_text = self._get_expired_text(guild_name)
        else:
            main_text = self._get_punishment_text(
                user=user,
                punish_type=punish_type,
                mode=mode,
            )

        container.add_item(
            TextDisplay[Self](
                f"## <:96965manager:1442917801953333389> {title}\n\n{main_text}"  # noqa: E501
            )
        )
        container.add_item(Separator[Self]())

        meta_description = self._get_meta_description(
            moderator_id=moderator_id,
            reason=reason,
            duration=duration,
            mode=mode,
            guild_name=guild_name,
        )
        container.add_item(TextDisplay[Self](meta_description))
        container.add_item(Separator[Self]())

        if mode != "expired":
            container.add_item(
                TextDisplay[Self](
                    "-# Если вы считаете, что это наказание было выдано...\n"
                    "-# ...ошибочно/несправедливо - обратитесь на [Arz Guard forum](https://forum.arzguard.com)."
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

    def _get_punishment_text(
        self,
        user: Member | User,
        punish_type: str,
        mode: str,
    ) -> str:
        """Get punishment description text based on mode.

        Args:
            user: Target user
            punish_type: Type of punishment (mute, ban, etc.)
            mode: "server" or "dm"

        Returns:
            Formatted punishment text
        """

        punishment_desc = PUNISHMENTS_DESC_DICT.get(mode, {}).get(
            punish_type,
            "был наказан." if mode == "server" else "были наказаны.",
        )

        if mode == "server":
            return f"**Пользователь {user.mention} {punishment_desc}**"
        else:
            return f"**Вы {punishment_desc}**"

    def _get_expired_text(self, server_name: str | None) -> str:
        """Get text for expired punishment notification.

        Args:
            server_name: Name of the server (optional)

        Returns:
            Formatted expired text
        """
        if server_name:
            return "**Срок вашего наказания на истёк.**"
        else:
            return "**Срок вашего наказания истёк.**"

    def _get_meta_description(
        self,
        moderator_id: int,
        reason: str,
        duration: str | None,
        mode: str,
        guild_name: str | None,
    ) -> str:
        """Get metadata description (moderator, reason, duration).

        Args:
            moderator_id: Moderator's ID
            reason: Punishment reason
            duration: Punishment duration (optional)
            mode: Current mode
            guild_name: Name of the guild

        Returns:
            Formatted metadata text
        """

        if mode == "expired":
            meta = f"> **Причина:** *{reason}*"
            if duration:
                meta += f"\n> **Длительность была: `{duration}`**"
            if guild_name:
                meta += f"\n> **Сервер: `{guild_name}`**"
            return meta

        meta = f"> **Модератор: <@{moderator_id}>**\n> **Причина:** *{reason}*"
        if duration:
            meta += f"\n> **Длительность: `{duration}`**"
        if guild_name:
            meta += f"\n> **Сервер: `{guild_name}`**"

        return meta
