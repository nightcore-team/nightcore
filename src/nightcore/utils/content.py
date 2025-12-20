"""Utilities related to content."""

import re


def has_url_in_content(content: str) -> bool:
    """Check if the content contains a URL."""
    url_pattern = re.compile(
        r"(https?://[^\s]+)|(www\.[^\s]+)",
        re.IGNORECASE,
    )
    return bool(url_pattern.search(content))


def is_image_url(url: str) -> bool:
    """Check if the URL points to an image based on file extension."""
    image_extensions = (
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".svg",
        ".webp",
        ".ico",
        ".tiff",
        ".tif",
    )
    # Remove query parameters and fragments
    url_without_params = url.split("?")[0].split("#")[0]
    return url_without_params.lower().endswith(image_extensions)
