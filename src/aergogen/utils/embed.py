from io import BytesIO
from typing import Optional

from discord import Embed, File
from PIL.Image import Image
from tqdm import tqdm


def embed_string(
    string: str,
    *,
    prompt: Optional[str] = None,
    icon: str = "⏳",
) -> Embed:
    embed = (
        Embed(title=prompt)
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


def embed_progress(
    progress: float,
    *,
    prompt: Optional[str] = None,
    icon: str = "⏳",
) -> Embed:
    embed = (
        Embed(title=prompt)
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


def embed_image(
    image: Image,
    *,
    prompt: Optional[str] = None,
) -> tuple[Embed, File]:
    with BytesIO() as buffer:
        image.save(buffer, format="PNG")
        buffer.seek(0)
        file = File(buffer, filename="image.png")

    embed = Embed(title=prompt)
    embed.set_image(url="attachment://image.png")
    return embed, file


def embed_counts(
    counts: dict[str, int],
    *,
    title: Optional[str] = None,
    total_per_channel: int = 50,
) -> Embed:
    embed = Embed(
        title=f"{title or 'total'}\n".upper()
        + tqdm.format_meter(
            n=sum(min(count, total_per_channel) for count in counts.values()),
            total=total_per_channel * len(counts),
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
                n=min(count, total_per_channel),
                total=total_per_channel,
                elapsed=0.0,
                bar_format=f"`[{{bar}}] {count}/{total_per_channel}`",
                ascii="-#",
                ncols=35,
            ),
            inline=False,
        )
    return embed
