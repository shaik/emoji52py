from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class EmojiDataset:
    version: str
    emoji_list: list[str]
    asset_paths: list[Path]
    features: np.ndarray


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "twemoji_png"


def load_dataset(version: str) -> EmojiDataset:
    index_path = DATA_DIR / f"emoji_index_{version}.json"
    features_path = DATA_DIR / f"emoji_features_{version}.npy"

    if not index_path.exists():
        raise FileNotFoundError(f"Missing dataset index: {index_path}")
    if not features_path.exists():
        raise FileNotFoundError(f"Missing dataset features: {features_path}")

    with index_path.open("r", encoding="utf-8") as f:
        index_data = json.load(f)

    emoji_list = index_data["emoji_list"]
    asset_paths = [ASSET_DIR / path for path in index_data["asset_paths"]]
    features = np.load(features_path)

    if len(emoji_list) != features.shape[0]:
        raise ValueError("Emoji list and feature array size mismatch")

    return EmojiDataset(
        version=index_data["version"],
        emoji_list=emoji_list,
        asset_paths=asset_paths,
        features=features,
    )
