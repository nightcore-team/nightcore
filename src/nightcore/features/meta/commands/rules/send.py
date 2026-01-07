"""Command to send the rules to a channel."""

import logging
from typing import cast

from discord import Embed, Guild, Interaction

from src.infra.db.models import MainGuildConfig
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.meta.utils import (
    build_rules_embeds,
    convert_dict_to_rules,
)
from src.nightcore.services.config import specified_guild_config
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

    async with specified_guild_config(
        bot=bot, guild_id=guild.id, config_type=MainGuildConfig, _create=True
    ) as (guild_config, _):
        rules_data = cast(
            dict[str, object], guild_config.guild_rules or {"chapters": []}
        )

    # json -> dataclass
    rules = convert_dict_to_rules(rules_data)

    chapters = rules.chapters

    if not chapters:
        await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка отправки правил",
                "Правила отсутствуют",
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )
        return

    await interaction.response.defer(thinking=True)
    messages: list[list[Embed]] = []

    # build and send embeds
    for chapter in chapters:
        title = f"{chapter.number}. {chapter.title}"
        text_lines: list[str] = []

        for rule in chapter.rules:
            # main rule
            text_lines.append(f"{rule.number}. {rule.text}")

            # subrule
            for subrule in rule.subrules:
                text_lines.append(f"{subrule.number}. {subrule.text}")

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
