"""Command to send the rules to a channel."""

import logging
from typing import cast

from discord import Embed, Guild, Interaction

from src.infra.db.operations import get_guild_rules
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.meta.utils import build_rules_embeds
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

from ._groups import rules as rules_group

logger = logging.getLogger(__name__)


@rules_group.command(
    name="send", description="Отправить правила в текущий канал"
)  # type: ignore
@check_required_permissions(PermissionsFlagEnum.HEAD_MODERATION_ACCESS)
async def send_rules(
    interaction: Interaction["Nightcore"],
):
    """Send the rules to a channel."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with bot.uow.start(readonly=True) as session:
        rules = await get_guild_rules(session, guild_id=guild.id)
        session.expunge_all()

    if rules is None or not rules.chapters:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки правил",
                "Правила отсутствуют",
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    chapters = rules.chapters

    if not chapters:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки правил",
                "Правила отсутствуют",
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    await interaction.response.defer(thinking=True)
    messages: list[list[Embed]] = []

    # build and send embeds
    for i, chapter in enumerate(chapters, start=1):
        title = f"{i}. {chapter.text}"
        text_lines: list[str] = []

        for j, rule in enumerate(chapter.rules, start=1):
            # main rule
            text_lines.append(f"{i}.{j}. {rule.text}")

            # subrules
            for k, subrule in enumerate(rule.subrules, start=1):
                text_lines.append(f"{i}.{j}.{k}. {subrule.text}")

        embeds_chunk = build_rules_embeds(title, text_lines)
        messages.extend(embeds_chunk)

    for embed_group in messages:
        await interaction.channel.send(embeds=embed_group)  # type: ignore

    await interaction.followup.send(
        embed=SuccessMoveEmbed(
            "Отправка правил",
            "Правила успешно отправлены",
            bot.user.display_name,  # type: ignore
            bot.user.avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked user=%s guild=%s",
        interaction.user.id,
        guild.id,
    )
