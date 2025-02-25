from __future__ import annotations

from discord import Interaction
from discord.abc import Messageable
from discord.app_commands import command, describe
from discord.ext.commands import Bot, Cog


class NotMessageable(Exception):
    pass


class Commands(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @command(name="gen", description="Generate an image from a prompt")
    @describe(prompt="aergo man eating a dominos pizza")
    async def gen(self, interaction: Interaction, prompt: str) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)

        if not isinstance(interaction.channel, Messageable):
            raise NotMessageable(interaction.channel_id)

        await interaction.channel.send(prompt)
        await interaction.delete_original_response()
