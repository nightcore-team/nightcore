from typing import cast  # noqa: D100

from discord import Embed, Guild, Interaction

from src.infra.db.models import MainGuildConfig
from src.infra.db.models._annot import Chapter, Rule, Rules
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.meta.utils import build_rules_embeds
from src.nightcore.services.config import specified_guild_config

from ._groups import rules as rules_group


@rules_group.command(name="send", description="Send rules to a channel")
async def send_rules(
    interaction: Interaction["Nightcore"],
):
    """Send the rules to a channel."""

    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with specified_guild_config(
        bot=bot, guild_id=guild.id, config_type=MainGuildConfig
    ) as (guild_config, _):
        rules_data = guild_config.guild_rules or {"chapters": []}

    rules = Rules(
        chapters=[
            Chapter(
                number=c["number"],  # type: ignore
                title=c["title"],  # type: ignore
                rules=[
                    Rule(
                        number=r["number"],  # type: ignore
                        text=r["text"],  # type: ignore
                        subrules=[
                            Rule(**sr)  # type: ignore
                            for sr in r.get("subrules", [])  # type: ignore
                        ],
                    )
                    for r in c["rules"]  # type: ignore
                ],
            )
            for c in rules_data["chapters"]  # type: ignore
        ]
    )

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
