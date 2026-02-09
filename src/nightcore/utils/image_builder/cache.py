"""Image and font caching module."""

from PIL.Image import Image as LoadedImage
from PIL.ImageFile import ImageFile
from PIL.ImageFont import FreeTypeFont


class ImageCache:
    def __init__(self) -> None:
        self._images: dict[str, ImageFile] = {}
        self._fonts: dict[str, dict[int, FreeTypeFont]] = {}

    def get_image(self, path: str):
        """Retrieve an image from cache."""

        return self._get_cached_image(path)

    def get_font(self, path: str, size: int):
        """Retrieve a font from cache."""

        return self._get_cached_font(path, size)

    def set_font(self, path: str, font: FreeTypeFont, size: int):
        """Caches a font object with the specified path and size."""

        if path not in self._fonts:
            self._fonts[path] = {}
        self._fonts[path][size] = font

    def set_image(self, path: str, image: ImageFile):
        """Caches an image object with the specified path."""

        self._images[path] = image

    def _get_cached_image(self, path: str) -> LoadedImage | None:
        image = self._images.get(path, None)

        if image is not None:
            return image.copy()

    def _get_cached_font(self, path: str, size: int) -> FreeTypeFont | None:
        if font := self._fonts.get(path, None):
            return font.get(size, None)
