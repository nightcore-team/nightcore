"""Special discord types for type hinting."""

from typing import Union

from discord import (
    ActionRow,
    Button,
    Component,
    FileComponent,
    MediaGalleryComponent,
    SectionComponent,
    SelectMenu,
    TextDisplay,
    TextInput,
    ThumbnailComponent,
)

ActionRowChildComponentType = Union["Button", "SelectMenu", "TextInput"]
SectionComponentType = Union["TextDisplay"]

MessageComponentType = Union[
    ActionRowChildComponentType,
    SectionComponentType,
    "ActionRow",
    "SectionComponent",
    "ThumbnailComponent",
    "MediaGalleryComponent",
    "FileComponent",
    "SectionComponent",
    "Component",
]
