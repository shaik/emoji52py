from __future__ import annotations

import base64
import io
import json
import random
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image

from app.api.schemas import CropPayload, SettingsPayload
from app.core.cache import ConversionCache, ConversionResult, EmojiImageCache, FeatureMemoCache
from app.core.dataset import load_dataset
from app.core.dithering import apply_dithering
from app.core.features import compute_grid_features
from app.core.hashing import deterministic_seed, stable_hash
from app.core.matcher import MatchWeights, match_features
from app.core.preprocess import compute_grid_size
from app.core.render import RenderSettings, render_mosaic

router = APIRouter(prefix="/api")

DATASET_VERSION = "v1"
DATASET = load_dataset(DATASET_VERSION)
CONVERSION_CACHE = ConversionCache(max_size=128)
EMOJI_IMAGE_CACHE = EmojiImageCache(max_size=1024)
FEATURE_MEMO_CACHE = FeatureMemoCache(max_size=4096)


@router.post("/convert")
async def convert_image(
    file: UploadFile = File(...),
    crop: Optional[str] = Form(None),
    settings: Optional[str] = Form(None),
) -> dict[str, Any]:
    if file.content_type not in {"image/png", "image/jpeg"}:
        raise HTTPException(status_code=400, detail="Only PNG and JPEG files are supported.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty upload.")

    try:
        settings_data = json.loads(settings) if settings else {}
        crop_data = json.loads(crop) if crop else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

    settings_payload = SettingsPayload.from_json(settings_data)
    crop_payload = CropPayload.model_validate(crop_data) if crop_data else CropPayload()

    image_hash = stable_hash(
        image_bytes,
        crop_payload.model_dump(),
        settings_payload.model_dump(),
        DATASET.version,
    )

    cached = CONVERSION_CACHE.get(image_hash)
    if cached is not None:
        return _response_from_cache(image_hash, cached)

    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Unable to decode image.") from exc

    image = image.convert("RGBA")
    width, height = image.size

    warnings: list[str] = []
    crop_x, crop_y, crop_w, crop_h = _normalize_crop(crop_payload, width, height, warnings)
    cropped = image.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))

    grid_result = compute_grid_size(
        crop_w,
        crop_h,
        settings_payload.max_dim,
        settings_payload.grid_w,
        settings_payload.grid_h,
        settings_payload.lock_aspect,
    )
    warnings.extend(grid_result.warnings)

    cell_features, _, _, _ = compute_grid_features(cropped, grid_result.grid_w, grid_result.grid_h)

    if settings_payload.dithering:
        warnings.append("Dithering is not yet implemented; using direct matching.")
        cell_features = apply_dithering(cell_features)

    rng = None
    if settings_payload.deterministic:
        seed = deterministic_seed(
            image_bytes,
            crop_payload.model_dump(),
            settings_payload.model_dump(),
            DATASET.version,
        )
        rng = random.Random(seed)

    weights = MatchWeights(
        color=settings_payload.weights.color,
        edge=settings_payload.weights.edge,
        alpha=settings_payload.weights.alpha,
    )

    indices = match_features(
        cell_features,
        DATASET.features,
        weights,
        settings_payload.deterministic,
        rng=rng,
        memo_cache=FEATURE_MEMO_CACHE,
    )

    grid = _indices_to_grid(indices, DATASET.emoji_list, grid_result.grid_w, grid_result.grid_h)
    grid_spaced = [" ".join(row) for row in grid]

    preview_png = _build_preview(grid, settings_payload, grid_result.grid_w, grid_result.grid_h)

    result = ConversionResult(
        grid=grid,
        grid_w=grid_result.grid_w,
        grid_h=grid_result.grid_h,
        grid_spaced=grid_spaced,
        preview_png=preview_png,
        dataset_version=DATASET.version,
        warnings=warnings,
    )
    CONVERSION_CACHE.set(image_hash, result)

    return _response_from_cache(image_hash, result, warnings)


@router.get("/export/text")
async def export_text(hash: str, spaced: int = 0) -> Response:
    cached = CONVERSION_CACHE.get(hash)
    if cached is None:
        raise HTTPException(status_code=404, detail="Unknown hash")
    lines = cached.grid_spaced if spaced else ["".join(row) for row in cached.grid]
    content = "\n".join(lines)
    headers = {"Content-Disposition": "attachment; filename=emoji-art.txt"}
    return Response(content=content, media_type="text/plain", headers=headers)


@router.get("/export/png")
async def export_png(hash: str, bg: str = "transparent", color: str = "#ffffff") -> Response:
    cached = CONVERSION_CACHE.get(hash)
    if cached is None:
        raise HTTPException(status_code=404, detail="Unknown hash")

    settings = RenderSettings(cell_size=48, bg_mode=bg, bg_color=color)
    png_bytes = render_mosaic(_grid_to_indices(cached.grid), DATASET.asset_paths, settings, EMOJI_IMAGE_CACHE, "png")
    headers = {"Content-Disposition": "attachment; filename=emoji-art.png"}
    return Response(content=png_bytes, media_type="image/png", headers=headers)


@router.get("/export/jpg")
async def export_jpg(hash: str, color: str = "#ffffff") -> Response:
    cached = CONVERSION_CACHE.get(hash)
    if cached is None:
        raise HTTPException(status_code=404, detail="Unknown hash")

    settings = RenderSettings(cell_size=48, bg_mode="solid", bg_color=color)
    jpg_bytes = render_mosaic(_grid_to_indices(cached.grid), DATASET.asset_paths, settings, EMOJI_IMAGE_CACHE, "jpg")
    headers = {"Content-Disposition": "attachment; filename=emoji-art.jpg"}
    return Response(content=jpg_bytes, media_type="image/jpeg", headers=headers)


def _normalize_crop(
    crop: CropPayload,
    width: int,
    height: int,
    warnings: list[str],
) -> tuple[int, int, int, int]:
    if crop.w <= 0 or crop.h <= 0:
        return 0, 0, width, height

    x = max(0, min(crop.x, width - 1))
    y = max(0, min(crop.y, height - 1))
    w = max(1, min(crop.w, width - x))
    h = max(1, min(crop.h, height - y))

    if (x, y, w, h) != (crop.x, crop.y, crop.w, crop.h):
        warnings.append("Crop rectangle adjusted to fit within image bounds.")

    return x, y, w, h


def _indices_to_grid(indices, emoji_list, grid_w, grid_h) -> list[list[str]]:
    grid: list[list[str]] = []
    for row in range(grid_h):
        row_indices = indices[row * grid_w : (row + 1) * grid_w]
        grid.append([emoji_list[idx] for idx in row_indices])
    return grid


def _grid_to_indices(grid: list[list[str]]) -> list[list[int]]:
    index_lookup = {emoji: idx for idx, emoji in enumerate(DATASET.emoji_list)}
    return [[index_lookup[emoji] for emoji in row] for row in grid]


def _build_preview(grid: list[list[str]], settings: SettingsPayload, grid_w: int, grid_h: int) -> Optional[bytes]:
    preview_size = 10
    if grid_w * preview_size > 1600 or grid_h * preview_size > 1600:
        return None
    render_settings = RenderSettings(
        cell_size=preview_size,
        bg_mode=settings.bg_mode,
        bg_color=settings.bg_color,
    )
    return render_mosaic(_grid_to_indices(grid), DATASET.asset_paths, render_settings, EMOJI_IMAGE_CACHE, "png")


def _response_from_cache(hash_value: str, cached: ConversionResult, extra_warnings: Optional[list[str]] = None) -> dict[str, Any]:
    grid_strings = ["".join(row) for row in cached.grid]
    warnings = list(cached.warnings)
    if extra_warnings:
        warnings.extend(extra_warnings)

    preview_b64 = None
    if cached.preview_png is not None:
        preview_b64 = base64.b64encode(cached.preview_png).decode("ascii")

    return {
        "grid_w": cached.grid_w,
        "grid_h": cached.grid_h,
        "grid": grid_strings,
        "grid_spaced": cached.grid_spaced,
        "preview_png_base64": preview_b64,
        "hash": hash_value,
        "warnings": warnings,
    }
