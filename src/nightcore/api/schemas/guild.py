"""API schemas."""

import discord
from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict

from ..types import DiscordId


class Base(BaseModel):
    """Base schema."""

    model_config = SettingsConfigDict(extra="ignore")


class GuildInfoSchema(Base):
    """Schema for a guild."""

    id: DiscordId
    name: str

    @staticmethod
    def from_discord(guild: discord.Guild) -> "GuildInfoSchema":
        """Create a GuildInfoSchema from a discord.Guild."""

        return GuildInfoSchema(id=guild.id, name=guild.name)


class RoleInfoSchema(Base):
    """Schema for a guild role."""

    id: DiscordId
    name: str
    color: str
    position: int
    administrator: bool

    @staticmethod
    def from_discord(role: discord.Role) -> "RoleInfoSchema":
        """Create a RoleInfoSchema from a discord.Role."""

        return RoleInfoSchema(
            id=role.id,
            name=role.name,
            color=str(role.color),
            position=role.position,
            administrator=role.permissions.administrator,
        )


class ChannelInfoSchema(Base):
    """Schema for a guild channel."""

    id: DiscordId
    name: str
    type: str

    @staticmethod
    def from_discord(channel: discord.abc.GuildChannel) -> "ChannelInfoSchema":
        """Create a ChannelInfoSchema from a discord.abc.GuildChannel."""

        return ChannelInfoSchema(
            id=channel.id,
            name=channel.name,
            type=str(channel.type),
        )


class MemberInfoShema(Base):
    """Schema for a guild member."""

    id: DiscordId
    roles: list[int]
    administrator: bool

    @staticmethod
    def from_discord(member: discord.Member) -> "MemberInfoShema":
        """Create a MemberInfoShema from a discord.Member."""
        return MemberInfoShema(
            id=member.id,
            roles=[role.id for role in member.roles],
            administrator=member.guild_permissions.administrator,
        )
