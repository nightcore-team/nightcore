"""Monkey-patch interaction send methods to log their execution time."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, cast

from discord.interactions import Interaction, InteractionResponse
from discord.webhook import Webhook, WebhookMessage

if TYPE_CHECKING:
    from src.nightcore.bot import Nightcore

WebhookSendT = WebhookMessage | None

logger = logging.getLogger(__name__)


def patch_interaction_send_methods(
    interaction: Interaction[Nightcore],
) -> None:
    """Monkey-patch interaction send methods to log their execution time."""
    _patch_send_message(interaction.response, "response.send_message")
    _patch_webhook_send(interaction.followup, "followup.send")


def _patch_send_message(
    obj: InteractionResponse[Nightcore],
    label: str,
) -> None:
    original = obj.send_message

    if getattr(original, "__patched__", False):
        return

    async def timed_send(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return await original(*args, **kwargs)
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            logger.info(
                "[time_executing/interaction] - %s took %.2f ms",
                label,
                elapsed,
            )

    timed_send.__patched__ = True  # type: ignore[attr-defined]
    obj.send_message = timed_send


def _patch_webhook_send(
    obj: Webhook,
    label: str,
) -> None:
    original = obj.send

    if getattr(original, "__patched__", False):
        return

    async def timed_send(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return cast(WebhookSendT, await original(*args, **kwargs))
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            logger.info(
                "[time_executing/interaction] - %s took %.2f ms",
                label,
                elapsed,
            )

    timed_send.__patched__ = True  # type: ignore[attr-defined]

    obj.send = timed_send
