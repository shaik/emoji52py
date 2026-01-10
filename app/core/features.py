from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class FeatureWeights:
    color: float = 1.0
    edge: float = 0.2
    alpha: float = 0.1


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    rgb = rgb.astype(np.float32)
    mask = rgb > 0.04045
    rgb_linear = np.where(mask, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)

    matrix = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ],
        dtype=np.float32,
    )
    xyz = rgb_linear @ matrix.T
    xyz /= np.array([0.95047, 1.0, 1.08883], dtype=np.float32)

    epsilon = 216 / 24389
    kappa = 24389 / 27

    def f(t: np.ndarray) -> np.ndarray:
        return np.where(t > epsilon, np.cbrt(t), (kappa * t + 16) / 116)

    f_xyz = f(xyz)
    l_val = 116 * f_xyz[..., 1] - 16
    a_val = 500 * (f_xyz[..., 0] - f_xyz[..., 1])
    b_val = 200 * (f_xyz[..., 1] - f_xyz[..., 2])

    return np.stack((l_val, a_val, b_val), axis=-1)


def sobel_magnitude(luma: np.ndarray) -> np.ndarray:
    luma = luma.astype(np.float32)
    padded = np.pad(luma, 1, mode="edge")

    gx = (
        padded[0:-2, 0:-2]
        + 2 * padded[1:-1, 0:-2]
        + padded[2:, 0:-2]
        - padded[0:-2, 2:]
        - 2 * padded[1:-1, 2:]
        - padded[2:, 2:]
    )
    gy = (
        padded[0:-2, 0:-2]
        + 2 * padded[0:-2, 1:-1]
        + padded[0:-2, 2:]
        - padded[2:, 0:-2]
        - 2 * padded[2:, 1:-1]
        - padded[2:, 2:]
    )
    return np.sqrt(gx ** 2 + gy ** 2)


def compute_image_feature(image: Image.Image) -> np.ndarray:
    image = image.convert("RGBA")
    data = np.asarray(image).astype(np.float32) / 255.0
    rgb = data[..., :3]
    alpha = data[..., 3]

    lab = rgb_to_lab(rgb)
    luma = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    edge = sobel_magnitude(luma)

    lab_mean = lab.reshape(-1, 3).mean(axis=0)
    edge_mean = float(edge.mean())
    alpha_cov = float((alpha > 0.1).mean())

    return np.array([lab_mean[0], lab_mean[1], lab_mean[2], edge_mean, alpha_cov], dtype=np.float32)


def compute_grid_features(
    image: Image.Image,
    grid_w: int,
    grid_h: int,
    sample: int = 4,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    image = image.convert("RGBA")
    target_w = max(1, grid_w * sample)
    target_h = max(1, grid_h * sample)
    resized = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
    data = np.asarray(resized).astype(np.float32) / 255.0
    rgb = data[..., :3]
    alpha = data[..., 3]

    lab = rgb_to_lab(rgb)
    luma = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    edge = sobel_magnitude(luma)

    lab_cells = lab.reshape(grid_h, sample, grid_w, sample, 3).mean(axis=(1, 3))
    alpha_cells = (alpha > 0.1).reshape(grid_h, sample, grid_w, sample).mean(axis=(1, 3))
    edge_cells = edge.reshape(grid_h, sample, grid_w, sample).mean(axis=(1, 3))

    features = np.concatenate(
        [
            lab_cells.reshape(-1, 3),
            edge_cells.reshape(-1, 1),
            alpha_cells.reshape(-1, 1),
        ],
        axis=1,
    ).astype(np.float32)

    return features, lab_cells, edge_cells, alpha_cells
