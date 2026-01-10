from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class GridResult:
    grid_w: int
    grid_h: int
    warnings: list[str]


def clamp_dim(value: int, max_dim: int) -> Tuple[int, Optional[str]]:
    if value > max_dim:
        return max_dim, f"Requested grid dimension {value} clamped to {max_dim}."
    if value < 1:
        return 1, f"Requested grid dimension {value} raised to 1."
    return value, None


def compute_grid_size(
    width: int,
    height: int,
    max_dim: int,
    grid_w: Optional[int],
    grid_h: Optional[int],
    lock_aspect: bool,
) -> GridResult:
    warnings: list[str] = []
    max_dim = min(max_dim, 120)

    if grid_w is None and grid_h is None:
        if width >= height:
            grid_w = max_dim
            grid_h = max(1, round(height / width * grid_w))
        else:
            grid_h = max_dim
            grid_w = max(1, round(width / height * grid_h))
    else:
        if grid_w is not None:
            grid_w, warning = clamp_dim(grid_w, max_dim)
            if warning:
                warnings.append(warning)
        if grid_h is not None:
            grid_h, warning = clamp_dim(grid_h, max_dim)
            if warning:
                warnings.append(warning)

        if grid_w is None:
            grid_w = max(1, round(width / height * grid_h))
        elif grid_h is None:
            grid_h = max(1, round(height / width * grid_w))

    if grid_w is None or grid_h is None:
        raise ValueError("Failed to compute grid size")

    if grid_w > max_dim:
        grid_w = max_dim
        warnings.append("Grid width clamped to max_dim.")
    if grid_h > max_dim:
        grid_h = max_dim
        warnings.append("Grid height clamped to max_dim.")

    return GridResult(grid_w=grid_w, grid_h=grid_h, warnings=warnings)
