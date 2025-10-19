"""Utilities for escaping Discord-flavored markdown to plain text."""

import re

# Regexes for various Discord/Markdown elements
RE_CODE_FENCE = re.compile(
    r"(?s)(`{3,})(?:[^\n`]*)\n(.*?)\n\1"
)  # ```lang\ncontent\n```
RE_INLINE_CODE = re.compile(r"`([^`]+?)`")
RE_SPOILER = re.compile(r"\|\|([\s\S]+?)\|\|")

RE_BOLD_IT_TRIPLE_AST = re.compile(r"\*{3}([\s\S]+?)\*{3}")
RE_BOLD_IT_TRIPLE_UND = re.compile(r"_{3}([\s\S]+?)_{3}")
RE_BOLD = re.compile(r"\*{2}([\s\S]+?)\*{2}")
RE_UNDERLINE = re.compile(r"__([\s\S]+?)__")
RE_STRIKE = re.compile(r"~~([\s\S]+?)~~")
# Safer match for single * and _
RE_ITALIC_AST = re.compile(r"(?<!\*)\*([^\s][\s\S]*?[^\s])\*(?!\*)")
RE_ITALIC_UND = re.compile(r"(?<!_)_([^\s][\s\S]*?[^\s])_(?!_)")

RE_BLOCKQUOTE = re.compile(r"(?m)^\s*>+\s?")
RE_HEADINGS = re.compile(r"(?m)^\s{0,3}#{1,6}\s+")
RE_ULIST = re.compile(r"(?m)^\s{0,3}[-*+]\s+")
RE_OLIST = re.compile(r"(?m)^\s{0,3}\d+\.\s+")

RE_MD_LINK = re.compile(r"\[([^\]]*?)\]\((\S+?)\)")
RE_MD_IMAGE = re.compile(r"!\[([^\]]*?)\]\((\S+?)\)")
RE_AUTO_ANGLE_LINK = re.compile(r"<(https?://[^>\s]+)>")

RE_USER_MENTION = re.compile(r"<@!?(?P<id>\d+)>")
RE_ROLE_MENTION = re.compile(r"<@&(?P<id>\d+)>")
RE_CHANNEL_MENTION = re.compile(r"<#(?P<id>\d+)>")
RE_CUSTOM_EMOJI = re.compile(r"<a?:(?P<name>[a-zA-Z0-9_~\-]+):\d+>")

# Unescaping markdown-escape (\* \_ \# etc.) to plain characters
RE_UNESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|>~])")


def strip_discord_markdown_to_plain(
    text: str, *, keep_links: bool = True
) -> str:
    """Strip Discord-flavored markdown from text, returning plain text."""

    if not text:
        return ""

    out = text

    # 1) Code blocks and inline code -> raw content
    #    Support fences of arbitrary length (>=3)
    out = RE_CODE_FENCE.sub(lambda m: m.group(2), out)
    out = RE_INLINE_CODE.sub(lambda m: m.group(1), out)

    # 2) Spoilers
    out = RE_SPOILER.sub(lambda m: m.group(1), out)

    # 3) Links and images
    def _repl_md_link(m: re.Match[str]) -> str:
        txt, url = m.group(1), m.group(2)
        txt = txt.strip()
        if keep_links:
            if txt:
                return f"{txt} ({url})"
            return url
        else:
            return txt or ""

    # images as "alt (url)" or "url"/"alt" depending on keep_links
    def _repl_md_image(m: re.Match[str]) -> str:
        alt, url = m.group(1).strip(), m.group(2)
        if keep_links:
            if alt:
                return f"{alt} ({url})"
            return url
        else:
            return alt or ""

    out = RE_MD_IMAGE.sub(_repl_md_image, out)
    out = RE_MD_LINK.sub(_repl_md_link, out)

    # Auto-links in angle brackets <https://...> -> remove angles
    out = RE_AUTO_ANGLE_LINK.sub(lambda m: m.group(1), out)

    # 4) Bold/italic/underline/strikethrough
    out = RE_BOLD_IT_TRIPLE_AST.sub(lambda m: m.group(1), out)
    out = RE_BOLD_IT_TRIPLE_UND.sub(lambda m: m.group(1), out)
    out = RE_BOLD.sub(lambda m: m.group(1), out)
    out = RE_UNDERLINE.sub(lambda m: m.group(1), out)
    out = RE_STRIKE.sub(lambda m: m.group(1), out)
    out = RE_ITALIC_AST.sub(lambda m: m.group(1), out)
    out = RE_ITALIC_UND.sub(lambda m: m.group(1), out)

    # 5) Quote/heading/list prefixes
    out = RE_BLOCKQUOTE.sub("", out)
    out = RE_HEADINGS.sub("", out)
    out = RE_ULIST.sub("", out)
    out = RE_OLIST.sub("", out)

    # 6) Mentions/emojis in angle brackets into a readable, no-ping form
    out = RE_USER_MENTION.sub(lambda m: f"@{m.group('id')}", out)
    out = RE_ROLE_MENTION.sub(lambda m: f"@role-{m.group('id')}", out)
    out = RE_CHANNEL_MENTION.sub(lambda m: f"#{m.group('id')}", out)
    out = RE_CUSTOM_EMOJI.sub(lambda m: f":{m.group('name')}:", out)

    # 7) Remove markdown-escape backslashes (\\* -> *)
    out = RE_UNESCAPE.sub(r"\1", out)

    # 8) Remove leftover single markdown symbols if they form empty wrappers
    #    (rarely needed in practice, but sometimes orphans remain)
    #    E.g., lines with solitary symbols at edges without alphanumerics.
    out = re.sub(r"(?m)^\s*`+\s*$", "", out)  # lone rows of backticks
    out = re.sub(r"(?m)^\s*[|]+\s*$", "", out)  # lone pipes (from tables)

    return out.strip()
