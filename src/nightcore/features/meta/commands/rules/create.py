"""Command to create chapters or rules."""

import json
import logging
from typing import Any, cast

from discord import Guild, Interaction, app_commands

from src.config.config import config
from src.infra.db.models import MainGuildConfig
from src.infra.db.models._annot import Chapter, Rule
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.meta.utils import (
    convert_dict_to_rules,
    parse_clause,
)
from src.nightcore.services.config import specified_guild_config
from src.nightcore.utils.permissions import (
    PermissionsFlagEnum,
    check_required_permissions,
)

from ._groups import rules as rules_group

logger = logging.getLogger(__name__)


@rules_group.command(name="create", description="Создать главу или правило")  # type: ignore
@app_commands.describe(
    text="Текст главы или правила",
    clause="Номер пункта (например, '1' для главы, '1.1' для правила, '1.1.1' для подпункта)",  # noqa: E501
)
@check_required_permissions(PermissionsFlagEnum.ADMINISTRATOR)
async def create_chapter_or_rule(
    interaction: Interaction["Nightcore"],
    text: str,
    clause: str | None = None,
):
    """Create a chapter or rule."""
    # check if user has permissions
    ...
    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    async with specified_guild_config(
        bot=bot, guild_id=guild.id, config_type=MainGuildConfig
    ) as (guild_config, _):
        rules_data = cast(
            dict[str, Any], guild_config.guild_rules or {"chapters": []}
        )

        # json -> dataclass
        rules = convert_dict_to_rules(rules_data)

        # if clause is None, we are adding a chapter
        if not clause:
            if len(text) > 256:
                await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка добавления главы",
                        "Слишком длинный заголовок (до 256 символов)",
                        bot.user.display_name,  # type: ignore
                        bot.user.avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                return

            new_chapter = Chapter(
                number=len(rules.chapters) + 1, title=text, rules=[]
            )
            rules.chapters.append(new_chapter)
            message = "Глава успешно добавлена!"

        else:
            indexes = parse_clause(clause)
            if not indexes:
                await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка добавления главы",
                        "Неверный ввод пункта правил или главы",
                        bot.user.display_name,  # type: ignore
                        bot.user.avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                return

            if len(text) > config.bot.EMBED_DESCRIPTION_LIMIT:
                await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка добавления правила",
                        f"Слишком длинное правило (до {config.bot.EMBED_DESCRIPTION_LIMIT} символов)",  # noqa: E501
                        bot.user.display_name,  # type: ignore
                        bot.user.avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                return

            if len(indexes) == 1:
                ch_index = indexes[0] - 1
                if ch_index >= len(rules.chapters):
                    await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка добавления главы",
                            "Указанной главы не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                    return

                chapter = rules.chapters[ch_index]
                new_rule = Rule(
                    number=f"{chapter.number}.{len(chapter.rules) + 1}",
                    text=text,
                    subrules=[],
                )
                chapter.rules.append(new_rule)
                message = "Правило добавлено!"

            # 2 levels: adding a subrule
            elif len(indexes) == 2:
                ch_index = indexes[0] - 1
                rule_index = indexes[1] - 1

                if ch_index >= len(rules.chapters):
                    await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка добавления главы",
                            "Указанной главы не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                    return
                if rule_index >= len(rules.chapters[ch_index].rules):
                    await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка добавления правила",
                            "Указанного правила не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                    return

                parent_rule = rules.chapters[ch_index].rules[rule_index]
                new_subrule = Rule(
                    number=f"{parent_rule.number}.{len(parent_rule.subrules) + 1}",  # noqa: E501
                    text=text,
                    subrules=[],
                )
                parent_rule.subrules.append(new_subrule)
                message = "Подправило добавлено!"

            else:
                await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка добавления правила",
                        "Нельзя добавить правило глубже второго уровня",
                        bot.user.display_name,  # type: ignore
                        bot.user.avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )
                return

        guild_config.guild_rules = json.loads(
            json.dumps(rules, default=lambda o: o.__dict__)
        )

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Изменение правил",
            message,
            bot.user.display_name,  # type: ignore
            bot.user.avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked user=%s guild=%s clause=%s text=%s",
        interaction.user.id,
        guild.id,
        clause,
        text,
    )
