import io
from pathlib import Path

from PIL import Image

from app.core.cache import EmojiImageCache
from app.core.render import RenderSettings, render_mosaic


def test_render_png_transparency(tmp_path: Path):
    transparent = tmp_path / "transparent.png"
    solid = tmp_path / "solid.png"

    Image.new("RGBA", (1, 1), color=(0, 0, 0, 0)).save(transparent)
    Image.new("RGBA", (1, 1), color=(255, 0, 0, 255)).save(solid)

    asset_paths = [transparent, solid]
    grid = [[0, 1]]
    settings = RenderSettings(cell_size=10, bg_mode="transparent", bg_color="#ffffff")
    cache = EmojiImageCache(max_size=4)

    png_bytes = render_mosaic(grid, asset_paths, settings, cache, "png")
    image = Image.open(io.BytesIO(png_bytes))
    assert image.mode == "RGBA"
    assert image.size == (20, 10)
    left_pixel = image.getpixel((2, 5))
    assert left_pixel[3] == 0


def test_render_jpg_solid_background(tmp_path: Path):
    solid = tmp_path / "solid.png"
    Image.new("RGBA", (1, 1), color=(0, 255, 0, 255)).save(solid)

    asset_paths = [solid]
    grid = [[0]]
    settings = RenderSettings(cell_size=8, bg_mode="solid", bg_color="#112233")
    cache = EmojiImageCache(max_size=4)

    jpg_bytes = render_mosaic(grid, asset_paths, settings, cache, "jpg")
    image = Image.open(io.BytesIO(jpg_bytes))
    assert image.mode == "RGB"
    assert image.size == (8, 8)
