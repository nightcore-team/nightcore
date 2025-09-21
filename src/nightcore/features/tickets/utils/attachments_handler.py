"""Utility for handling attachments in ticket channels."""

import discord
from chat_exporter import AttachmentToDiscordChannelHandler  # type: ignore


class CustomAttachmentsHandler:
    def __init__(self, channel: discord.TextChannel) -> None:
        self.channel = channel
        self.handler = AttachmentToDiscordChannelHandler(channel=channel)
