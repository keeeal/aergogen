import uuid
from asyncio import sleep
from queue import Queue
from threading import Thread
from typing import Any, Optional
from uuid import UUID

from diffusers.pipelines import DiffusionPipeline, ImagePipelineOutput
from discord import Intents, Interaction, WebhookMessage
from discord.app_commands import command, describe
from discord.ext.commands import Bot, Cog
from PIL.Image import Image
from pydantic import BaseModel, ConfigDict, model_validator
from torch import Tensor
from tqdm import tqdm

from aergogen.utils.embed import embed_image, embed_progress, embed_string
from aergogen.utils.logging import get_logger

LOGGER = get_logger(__name__)

MODEL_LOADED_UUID = UUID(int=0)


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


def model_thread(requests: Queue, responses: dict[UUID, Response]) -> None:
    pipeline = DiffusionPipeline.from_pretrained("RunDiffusion/Juggernaut-XL-v8")
    pipeline.load_lora_weights("assets/aergo.safetensors")
    responses[MODEL_LOADED_UUID] = Response(progress=1.0)

    def progress_callback(
        pipeline: DiffusionPipeline,
        step: int,
        time: Tensor,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        responses[request.id] = Response(
            progress=(step + 1) / request.num_inference_steps
        )
        return data

    while True:
        request: Request = requests.get()
        LOGGER.info(f"Request: {request.prompt}")
        responses[request.id] = Response(progress=0.0)
        output: ImagePipelineOutput = pipeline(
            prompt=request.prompt,
            num_inference_steps=request.num_inference_steps,
            width=request.width,
            height=request.height,
            callback_on_step_end=progress_callback,
        )
        responses[request.id] = Response(image=output.images[0])
        requests.task_done()


class AergoGen(Bot):
    def __init__(self, command_prefix: str):
        intents = Intents.default()
        super().__init__(command_prefix, intents=intents)
        self.requests: Queue = Queue()
        self.responses: dict[UUID, Response] = {}
        Thread(target=model_thread, args=(self.requests, self.responses)).start()

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

    def submit(self, request: Request) -> UUID:
        self.requests.put(request)
        return request.id

    def check_response(self, request_id: UUID) -> Optional[Response]:
        return self.responses.pop(request_id, None)


class Commands(Cog):
    def __init__(self, bot: AergoGen):
        self.bot = bot

    @command(name="gen", description="Generate an image from a prompt")
    @describe(prompt="eg: aergo man eating a dominos pizza")
    async def gen(self, interaction: Interaction, prompt: str) -> None:
        await interaction.response.defer(thinking=True, ephemeral=True)
        request_id = self.bot.submit(Request(prompt=prompt))
        await sleep(2)

        followup: WebhookMessage = await interaction.followup.send(
            embed=embed_string("In queue...")
        )

        while True:
            response = self.bot.check_response(request_id)
            if response:
                if response.image:
                    embed, file = embed_image(response.image, prompt)
                    await interaction.delete_original_response()
                    await interaction.channel.send(embed=embed, file=file)
                    break
                await followup.edit(embed=embed_progress(response.progress))
            await sleep(1)
