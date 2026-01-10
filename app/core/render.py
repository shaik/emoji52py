from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image

from app.core.cache import EmojiImageCache, EmojiImageKey


@dataclass(frozen=True)
class RenderSettings:
    cell_size: int
    bg_mode: str
    bg_color: str


def _parse_hex_color(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    if len(value) != 6:
        raise ValueError("Invalid color format")
    return tuple(int(value[i : i + 2], 16) for i in range(0, 6, 2))


def _load_emoji_image(path: Path, size: int, cache: EmojiImageCache) -> Image.Image:
    key = EmojiImageKey(path=str(path), size=size)
    cached = cache.get(key)
    if cached is not None:
        return cached
    image = Image.open(path).convert("RGBA")
    resized = image.resize((size, size), Image.Resampling.LANCZOS)
    cache.set(key, resized)
    return resized


def render_mosaic(
    grid_indices: list[list[int]],
    asset_paths: list[Path],
    settings: RenderSettings,
    cache: EmojiImageCache,
    output_format: str,
) -> bytes:
    grid_h = len(grid_indices)
    grid_w = len(grid_indices[0]) if grid_h else 0
    width = grid_w * settings.cell_size
    height = grid_h * settings.cell_size

    bg_rgb = _parse_hex_color(settings.bg_color) if settings.bg_mode == "solid" else None

    if output_format.lower() == "jpg":
        if bg_rgb is None:
            raise ValueError("JPG export requires solid background")
        canvas = Image.new("RGB", (width, height), color=bg_rgb)
    else:
        canvas = Image.new("RGBA", (width, height), color=(0, 0, 0, 0))
        if bg_rgb is not None:
            background = Image.new("RGBA", (width, height), color=(*bg_rgb, 255))
            canvas.paste(background)

    for row_idx, row in enumerate(grid_indices):
        for col_idx, emoji_idx in enumerate(row):
            asset_path = asset_paths[emoji_idx]
            emoji_image = _load_emoji_image(asset_path, settings.cell_size, cache)
            x = col_idx * settings.cell_size
            y = row_idx * settings.cell_size
            if canvas.mode == "RGB":
                canvas.paste(emoji_image.convert("RGB"), (x, y))
            else:
                canvas.paste(emoji_image, (x, y), mask=emoji_image)

    buffer = io.BytesIO()
    if output_format.lower() == "jpg":
        canvas.save(buffer, format="JPEG", quality=92)
    else:
        canvas.save(buffer, format="PNG")
    return buffer.getvalue()
