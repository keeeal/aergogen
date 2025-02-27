from io import BytesIO
from typing import Optional

from discord import Embed, File
from PIL.Image import Image
from tqdm import tqdm


def embed_string(string: str) -> Embed:
    embed = (
        Embed()
        .add_field(
            name="🚀",
            value="",
        )
        .add_field(
            name="",
            value=string,
        )
    )
    return embed


def embed_progress(progress: float) -> Embed:
    embed = (
        Embed()
        .add_field(
            name="🚀",
            value="",
        )
        .add_field(
            name="",
            value=tqdm.format_meter(
                n=progress,
                total=1.0,
                elapsed=0.0,
                bar_format="`[{bar}] {percentage:.0f}%`",
                ascii="-#",
                ncols=35,
            ),
        )
    )
    return embed


def embed_image(image: Image, prompt: Optional[str] = None) -> tuple[Embed, File]:
    with BytesIO() as buffer:
        image.save(buffer, format="PNG")
        buffer.seek(0)
        file = File(buffer, filename="image.png")

    embed = Embed(description=prompt)
    embed.set_image(url="attachment://image.png")
    return embed, file
