"""Command to create chapters or rules."""

import logging
from typing import cast

from discord import Guild, Interaction, app_commands

from src.config.config import config
from src.infra.db.models.configurations.rules import (
    GuildRules,
    GuildRulesChapter,
    GuildRulesRule,
    GuildRulesSubRule,
)
from src.infra.db.operations import get_guild_rules
from src.nightcore.bot import Nightcore
from src.nightcore.components.embed import ErrorEmbed, SuccessMoveEmbed
from src.nightcore.features.meta.utils import parse_clause
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
@check_required_permissions(PermissionsFlagEnum.HEAD_MODERATION_ACCESS)
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

    async with bot.uow.start() as session:
        rules = cast(
            GuildRules,
            await get_guild_rules(
                session,
                guild_id=guild.id,
            ),
        )

        # if clause is None, we are adding a chapter
        if not clause:
            if len(text) > 256:
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка добавления главы",
                        "Слишком длинный заголовок (до 256 символов)",
                        bot.user.display_name,  # type: ignore
                        bot.user.avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            new_chapter = GuildRulesChapter(rules_id=rules.id, text=text)
            session.add(new_chapter)
            message = "Глава успешно добавлена!"

        else:
            indexes = parse_clause(clause)
            if not indexes:
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка добавления главы",
                        "Неверный ввод пункта правил или главы",
                        bot.user.display_name,  # type: ignore
                        bot.user.avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            if len(text) > config.bot.EMBED_DESCRIPTION_LIMIT:
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка добавления правила",
                        f"Слишком длинное правило (до {config.bot.EMBED_DESCRIPTION_LIMIT} символов)",  # noqa: E501
                        bot.user.display_name,  # type: ignore
                        bot.user.avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

            if len(indexes) == 1:
                ch_index = indexes[0] - 1
                if ch_index >= len(rules.chapters):
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка добавления правила",
                            "Указанной главы не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

                chapter = rules.chapters[ch_index]
                new_rule = GuildRulesRule(chapter_id=chapter.id, text=text)
                session.add(new_rule)
                message = "Правило добавлено!"

            # 2 levels: adding a subrule
            elif len(indexes) == 2:
                ch_index = indexes[0] - 1
                rule_index = indexes[1] - 1

                if ch_index >= len(rules.chapters):
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка добавления главы",
                            "Указанной главы не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                if rule_index >= len(rules.chapters[ch_index].rules):
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка добавления правила",
                            "Указанного правила не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

                parent_rule = rules.chapters[ch_index].rules[rule_index]
                new_subrule = GuildRulesSubRule(
                    rule_id=parent_rule.id, text=text
                )
                session.add(new_subrule)
                message = "Подправило добавлено!"

            else:
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка добавления правила",
                        "Нельзя добавить правило глубже второго уровня",
                        bot.user.display_name,  # type: ignore
                        bot.user.avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
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
