from io import BytesIO
from typing import Optional

from discord import Embed, File
from PIL.Image import Image
from tqdm import tqdm


def embed_string(string: str, icon: str = "⏳") -> Embed:
    embed = (
        Embed()
        .add_field(
            name=icon,
            value="",
        )
        .add_field(
            name="",
            value=string,
        )
    )
    return embed


def embed_progress(progress: float, icon: str = "🚀") -> Embed:
    embed = (
        Embed()
        .add_field(
            name=icon,
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


def embed_counts(counts: dict[str, int], title: Optional[str] = None) -> Embed:
    embed = Embed(
        title=f"{title or 'total'}\n".upper()
        + tqdm.format_meter(
            n=sum(min(count, 50) for count in counts.values()),
            total=50 * len(counts),
            elapsed=0.0,
            bar_format="`[{bar}] {percentage:.0f}%`",
            ascii="-#",
            ncols=35,
        )
    )
    for channel, count in counts.items():
        embed.add_field(
            name=channel,
            value=tqdm.format_meter(
                n=min(count, 50),
                total=50,
                elapsed=0.0,
                bar_format=f"`[{{bar}}] {count}/50`",
                ascii="-#",
                ncols=35,
            ),
            inline=False,
        )
    return embed
