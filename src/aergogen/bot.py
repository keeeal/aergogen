from discord import Intents
from discord.ext.commands import Bot

from aergogen.commands import Commands
from aergogen.utils.logging import get_logger

LOGGER = get_logger(__name__)


class AergoGen(Bot):
    def __init__(self, command_prefix: str):
        intents = Intents.default()
        super().__init__(command_prefix, intents=intents)

    async def on_ready(self) -> None:
        await self.add_cog(Commands(bot=self))
        await self.tree.sync()

        LOGGER.info("READY")
