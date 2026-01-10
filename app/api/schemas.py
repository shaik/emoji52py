from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CropPayload(BaseModel):
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


class WeightPayload(BaseModel):
    color: float = 1.0
    edge: float = 0.2
    alpha: float = 0.1


class SettingsPayload(BaseModel):
    max_dim: int = 120
    grid_w: Optional[int] = None
    grid_h: Optional[int] = None
    lock_aspect: bool = True
    dithering: bool = False
    deterministic: bool = True
    emoji_set: Optional[str] = "full"
    bg_mode: str = "transparent"
    bg_color: str = "#ffffff"
    weights: WeightPayload = Field(default_factory=WeightPayload)

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "SettingsPayload":
        return cls.model_validate(payload)
