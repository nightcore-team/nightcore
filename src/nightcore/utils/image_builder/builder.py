"""A utility for creating and manipulating images with text for Discord."""

import io

import aiofiles
import discord
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Image as LoadedImage
from PIL.ImageFont import FreeTypeFont

from src.nightcore.utils.image_builder.cache import ImageCache
from src.nightcore.utils.image_builder.errors import ImageNotLoadedError


class ImageBuilder:
    def __init__(self, cache: ImageCache | None = None) -> None:
        self._cache = cache
        self.image = None
        self.font = None

    async def load_image(self, path: str):
        """Loads an image from the specified path using cache if available."""

        if self._cache is not None:
            self.image = self._cache.get_image(path)

        if self.image is None:
            self.image = await self._load_image(path)

    async def load_font(self, path: str, size: int):
        """Loads a font from the specified path and size using cache if available."""  # noqa: E501

        if self._cache is not None:
            self.font = self._cache.get_font(path, size)

        if self.font is None:
            self.font = await self._load_font(path, size)

    def draw_text(
        self,
        coords: tuple[int, int],
        text: str,
        align: str = "left",
        fill: str = "#000000",
    ):
        """Write text onto the image at the specified coordinates."""

        if self.image is None:
            raise ImageNotLoadedError()

        draw_text = ImageDraw.Draw(self.image)

        draw_text.text(
            xy=coords, text=text, font=self.font, align=align, fill=fill
        )

    def convert_to_discord(self):
        """Convert the image to a Discord-compatible File object."""

        if self.image is None:
            raise ImageNotLoadedError()

        with io.BytesIO() as image_buffer:
            self.image.save(image_buffer, "png")
            image_buffer.seek(0)

            return discord.File(fp=image_buffer, filename="image.png")

    async def _load_image(self, path: str) -> LoadedImage:
        async with aiofiles.open(path, "rb") as f:
            content = await f.read()

        image = Image.open(io.BytesIO(content))

        if self._cache is not None:
            self._cache.set_image(path, image)

        return image.copy()

    async def _load_font(self, path: str, size: int) -> FreeTypeFont:
        async with aiofiles.open(path, "rb") as f:
            content = await f.read()

        font = ImageFont.truetype(io.BytesIO(content), size=size)

        if self._cache is not None:
            self._cache.set_font(path, font, size)

        return font

    async def save(self, path: str):
        """Save the current image to the specified file path in PNG format."""

        if self.image is None:
            raise ImageNotLoadedError()

        buffer = io.BytesIO()
        self.image.save(buffer, format="PNG")

        async with aiofiles.open(path, "wb") as file:
            await file.write(buffer.getbuffer())
