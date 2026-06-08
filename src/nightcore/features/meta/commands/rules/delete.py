"""Command to delete chapters or rules."""

import logging
from typing import cast

from discord import Guild, Interaction, app_commands

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


@rules_group.command(name="delete", description="Удалить главу или правило")  # type: ignore
@app_commands.describe(
    clause="Номер пункта (например, '1' для главы, '1.1' для правила, '1.1.1' для подпункта)",  # noqa: E501
)
@check_required_permissions(PermissionsFlagEnum.HEAD_MODERATION_ACCESS)
async def delete_chapter_or_rule(
    interaction: Interaction["Nightcore"],
    clause: str,
):
    """Delete a chapter or rule."""
    bot = interaction.client
    guild = cast(Guild, interaction.guild)

    # load ORM rules
    indexes = parse_clause(clause)
    if not indexes:
        return await interaction.response.send_message(
            embed=ErrorEmbed(
                "Ошибка удаления главы или правила",
                "Неверный ввод пункта правил или главы",
                bot.user.display_name,  # type: ignore
                bot.user.avatar.url,  # type: ignore
            ),
            ephemeral=True,
        )

    async with bot.uow.start() as session:
        rules = await get_guild_rules(session, guild_id=guild.id)
        if rules is None:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка удаления главы или правила",
                    "Правила отсутствуют",
                    bot.user.display_name,  # type: ignore
                    bot.user.avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

        try:
            if len(indexes) == 1:
                ch_index = indexes[0] - 1
                if ch_index >= len(rules.chapters):
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления главы",
                            "Указанной главы не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

                # delete chapter ORM instance
                chapter = rules.chapters[ch_index]
                await session.delete(chapter)
                message = "Глава успешно удалена!"

            elif len(indexes) == 2:
                ch_index = indexes[0] - 1
                rule_index = indexes[1] - 1
                if ch_index >= len(rules.chapters):
                    await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления главы",
                            "Указанной главы не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                    return
                chapter = rules.chapters[ch_index]
                if rule_index >= len(chapter.rules):
                    await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления правила",
                            "Указанного правила не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )
                    return

                rule = chapter.rules[rule_index]
                await session.delete(rule)
                message = "Правило успешно удалено!"

            elif len(indexes) == 3:
                ch_index = indexes[0] - 1
                rule_index = indexes[1] - 1
                subrule_index = indexes[2] - 1

                if ch_index >= len(rules.chapters):
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления главы",
                            "Указанной главы не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

                chapter = rules.chapters[ch_index]
                if rule_index >= len(chapter.rules):
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления правила",
                            "Указанного правила не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

                rule = chapter.rules[rule_index]
                if subrule_index >= len(rule.subrules):
                    return await interaction.response.send_message(
                        embed=ErrorEmbed(
                            "Ошибка удаления подправила",
                            "Указанного подправила не существует",
                            bot.user.display_name,  # type: ignore
                            bot.user.avatar.url,  # type: ignore
                        ),
                        ephemeral=True,
                    )

                sub = rule.subrules[subrule_index]
                await session.delete(sub)
                message = "Подправило успешно удалено!"

            else:
                return await interaction.response.send_message(
                    embed=ErrorEmbed(
                        "Ошибка удаления подправила",
                        "Глубже третьего уровня нельзя удалять!",
                        bot.user.display_name,  # type: ignore
                        bot.user.avatar.url,  # type: ignore
                    ),
                    ephemeral=True,
                )

        except Exception:
            return await interaction.response.send_message(
                embed=ErrorEmbed(
                    "Ошибка при удалении",
                    "Произошла ошибка при удалении",
                    bot.user.display_name,  # type: ignore
                    bot.user.avatar.url,  # type: ignore
                ),
                ephemeral=True,
            )

    await interaction.response.send_message(
        embed=SuccessMoveEmbed(
            "Удаление главы или правила",
            message
            + "\n\nНе забудьте заново опубликовать правила командой /rules send",  # noqa: E501
            bot.user.display_name,  # type: ignore
            bot.user.avatar.url,  # type: ignore
        ),
        ephemeral=True,
    )

    logger.info(
        "[command] - invoked user=%s guild=%s clause=%s",
        interaction.user.id,
        guild.id,
        clause,
    )
