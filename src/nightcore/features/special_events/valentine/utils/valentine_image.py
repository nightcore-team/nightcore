"""Generate Valentine's Day themed images with custom text for Discord."""

from typing import Final

import discord

from src.nightcore.utils.image_builder.builder import ImageBuilder

FONT_SIZE: Final[int] = 45

VALENTINE_FONT_PATH: Final[str] = "assets/valentines_day/font.otf"
VALENTINE_IMAGE: Final[
    tuple[
        str, tuple[int, int], tuple[int, int]
    ]  # PATH, CENTER COORDS, UPPER LEFT COORDS
] = ("assets/valentines_day/image.png", (625, 400), (625, 117))

LINE_SIZE: Final[int] = 35
CENTER_LINES_COUNT = 3
LINE_INTERVAL_PIXELS: Final[int] = 55


async def generate_valentine_image(text: str) -> discord.File:
    """Create a Valentine-themed image with wrapped text and return as Discord file."""  # noqa: E501

    image_path, center_coords, upper_coords = VALENTINE_IMAGE

    coords = upper_coords
    align = "left"

    image_builder = ImageBuilder()

    await image_builder.load_image(image_path)
    await image_builder.load_font(VALENTINE_FONT_PATH, FONT_SIZE)

    lines: list[str] = []

    words = text.split()

    current_line = ""

    for word in words:
        if len(current_line) + len(word + " ") < LINE_SIZE:
            current_line += word + " "
        else:
            lines.append(current_line)
            current_line = word + " "

    if current_line:
        lines.append(current_line)

    if len(lines) <= CENTER_LINES_COUNT:
        coords = center_coords

    x_coord, y_coord = coords

    for line in lines:
        image_builder.draw_text(
            coords=(x_coord, y_coord), text=line, align=align
        )

        y_coord += LINE_INTERVAL_PIXELS

    return image_builder.convert_to_discord()
