import uuid
from asyncio import gather, sleep
from enum import StrEnum
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Any, Optional
from uuid import UUID

import torch
from diffusers.pipelines import (
    DiffusionPipeline,
    ImagePipelineOutput,
    StableDiffusionXLPipeline,
)
from discord import Attachment, CategoryChannel, Intents, Interaction
from discord.app_commands import command, describe
from discord.enums import ButtonStyle, InteractionType
from discord.ext.commands import Bot, Cog
from discord.ui import Button, View
from PIL.Image import Image
from pydantic import BaseModel, ConfigDict, model_validator
from torch import Tensor

from aergogen.utils.asyncio import gather_with_concurrency as gather
from aergogen.utils.embed import embed_counts, embed_image, embed_progress, embed_string
from aergogen.utils.logging import get_logger

LOGGER = get_logger(__name__)

MODEL_LOADED_UUID = UUID(int=0)


async def save_attachment(
    attachment: Attachment,
    directory: Path,
    filename: Optional[str] = None,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    await attachment.save(directory / (filename or attachment.filename))


class Unique(BaseModel):
    id: UUID

    @model_validator(mode="before")
    @classmethod
    def id_validator(cls, data: dict[str, Any]) -> dict[str, Any]:
        if not data.get("id"):
            data["id"] = uuid.uuid4()
        return data


class Request(Unique):
    prompt: str
    num_inference_steps: int = 2
    width: int = 512
    height: int = 512


class Response(Unique):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    progress: float = 0.0
    image: Optional[Image] = None
    cancelled: bool = False


def model_thread(
    requests: Queue,
    cancellations: dict[UUID, bool],
    responses: dict[UUID, Response],
) -> None:
    pipeline: StableDiffusionXLPipeline = DiffusionPipeline.from_pretrained(
        "RunDiffusion/Juggernaut-XL-v8"
    )
    pipeline.load_lora_weights("assets/hexix.safetensors")
    responses[MODEL_LOADED_UUID] = Response(progress=1.0)

    def progress_callback(
        pipeline: StableDiffusionXLPipeline,
        step: int,
        time: Tensor,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        if cancellations.pop(request.id, False):
            LOGGER.info(f"Cancelled: {request.prompt}")
            pipeline._interrupt = True
        responses[request.id] = Response(
            progress=(step + 1) / request.num_inference_steps,
            cancelled=pipeline.interrupt,
        )
        return data

    while request := Request.model_validate(requests.get()):
        if cancellations.pop(request.id, False):
            LOGGER.info(f"Cancelled: {request.prompt}")
            responses[request.id] = Response(cancelled=True)
            requests.task_done()
            continue

        LOGGER.info(f"Processing: {request.prompt}")
        responses[request.id] = Response(progress=0.0)
        output: ImagePipelineOutput = pipeline(
            prompt=request.prompt,
            num_inference_steps=request.num_inference_steps,
            width=request.width,
            height=request.height,
            callback_on_step_end=progress_callback,
        )
        responses[request.id] = Response(
            progress=1.0,
            image=output.images[0],
            cancelled=pipeline.interrupt,
        )
        requests.task_done()


class Action(StrEnum):
    CANCEL = "cancel"


class AergoGen(Bot):
    def __init__(
        self,
        command_prefix: str,
        home_guild_id: int,
        home_user_id: int,
        num_threads: int,
    ):
        intents = Intents.default()
        intents.message_content = True
        super().__init__(command_prefix, intents=intents)
        self.requests: Queue = Queue()
        self.cancellations: dict[UUID, bool] = {}
        self.responses: dict[UUID, Response] = {}
        self.home_guild_id = home_guild_id
        self.home_user_id = home_user_id

        if num_threads > 0:
            LOGGER.info(f"Setting num threads to {num_threads}")
            torch.set_num_threads(num_threads)

        Thread(
            target=model_thread,
            args=(self.requests, self.cancellations, self.responses),
        ).start()

    async def on_ready(self) -> None:
        LOGGER.info(f"Logged in as {self.user}")
        await self.add_cog(Commands(bot=self))
        await self.tree.sync()

        while True:
            response = self.check_response(MODEL_LOADED_UUID)
            if response and response.progress == 1.0:
                break
            await sleep(1)
            continue

        LOGGER.info("Model loaded")

    async def on_interaction(self, interaction: Interaction) -> None:
        if not interaction.type == InteractionType.component:
            return
        if not interaction.data or not interaction.message:
            return

        data = dict(interaction.data)
        custom_id = str(data["custom_id"])
        request_id, action = custom_id.split("/")
        request_id = UUID(request_id)
        action = Action(action)

        if action == Action.CANCEL:
            self.cancellations[request_id] = True
            await interaction.message.delete()
            return await interaction.response.send_message(
                embed=embed_string("🗑️ -- Gen cancelled"),
                ephemeral=True,
            )

    def submit_request(self, request: Request) -> UUID:
        LOGGER.info(f"Request: {request.prompt}")
        self.requests.put(request)
        return request.id

    def check_response(self, request_id: UUID) -> Optional[Response]:
        return self.responses.pop(request_id, None)

    async def fetch_attachments(self) -> dict[str, dict[str, list[Attachment]]]:
        home = await self.fetch_guild(self.home_guild_id)
        channels = await home.fetch_channels()
        categories = {
            category.id: category.name
            for category in channels
            if isinstance(category, CategoryChannel)
        }
        attachments: dict[str, dict[str, list[Attachment]]] = {}

        for channel in channels:
            if channel.category_id not in categories:
                continue
            category_name = categories[channel.category_id]
            if category_name not in attachments:
                attachments[category_name] = {}
            attachments[category_name][channel.name] = []
            async for message in channel.history(limit=None):
                for attachment in message.attachments:
                    attachments[category_name][channel.name].append(attachment)

        return attachments


class Buttons(View):
    def __init__(self, request_id: UUID) -> None:
        super().__init__(timeout=None)
        self.add_item(
            Button(
                label=Action.CANCEL.value,
                custom_id=f"{request_id}/{Action.CANCEL.value}",
                style=ButtonStyle.grey,
            )
        )


class Commands(Cog):
    def __init__(self, bot: AergoGen):
        self.bot = bot

    @command(name="count", description="Count the images in each channel")
    async def count(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=True)
        attachments = await self.bot.fetch_attachments()

        counts = {
            category_name: {
                channel_name: len(channel_attachments)
                for channel_name, channel_attachments in channels.items()
            }
            for category_name, channels in attachments.items()
        }
        await interaction.followup.send(
            embeds=[
                embed_counts(counts, title=category_name)
                for category_name, counts in counts.items()
            ]
        )

    @command(name="scrape", description="Scrape the images from each channel")
    async def scrape(self, interaction: Interaction) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        if interaction.user.id != self.bot.home_user_id:
            return await interaction.followup.send(
                embed=embed_string(
                    "🛑 -- I'm sorry, Dave. I'm afraid I can't do that.",
                )
            )

        attachments = await self.bot.fetch_attachments()

        root = Path("data")
        await gather(
            *[
                save_attachment(
                    attachment=attachment,
                    directory=root / category_name / channel_name,
                    filename=f"{attachment.id}-{attachment.filename}",
                )
                for category_name, channels in attachments.items()
                for channel_name, channel_attachments in channels.items()
                for attachment in channel_attachments
            ],
            concurrency=8,
        )

        await interaction.followup.send(embed=embed_string("✅ -- Done!"))

    @command(name="gen", description="Generate an image from a prompt")
    @describe(prompt="eg: aergo man eating a dominos pizza")
    async def gen(self, interaction: Interaction, prompt: str) -> None:
        request_id = self.bot.submit_request(Request(prompt=prompt))
        callback = await interaction.response.send_message(
            embed=embed_string(f"⏳ -- In queue...", prompt=prompt),
            view=Buttons(request_id),
        )
        message = await interaction.channel.fetch_message(callback.message_id)

        while True:
            response = self.bot.check_response(request_id)

            if response is None:
                await sleep(1)
                continue

            if response.cancelled:
                break

            if response.image:
                embed, file = embed_image(response.image, prompt=prompt)
                await message.edit(embed=embed, attachments=[file], view=None)
                break

            await message.edit(
                embed=embed_progress(response.progress, prompt=prompt)
            )
