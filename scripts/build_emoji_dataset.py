from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.features import compute_image_feature


def parse_codepoints(name: str) -> str:
    parts = name.split("-")
    return "".join(chr(int(part, 16)) for part in parts)


def build_dataset(asset_dir: Path, output_dir: Path, version: str) -> None:
    asset_paths = sorted(asset_dir.glob("*.png"))
    if not asset_paths:
        raise RuntimeError(f"No PNG assets found in {asset_dir}")

    emoji_list: list[str] = []
    rel_paths: list[str] = []
    features: list[np.ndarray] = []

    for path in asset_paths:
        emoji = parse_codepoints(path.stem)
        image = Image.open(path)
        feature = compute_image_feature(image)
        emoji_list.append(emoji)
        rel_paths.append(path.name)
        features.append(feature)

    index_data = {
        "version": version,
        "emoji_list": emoji_list,
        "asset_paths": rel_paths,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"emoji_index_{version}.json").write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    np.save(output_dir / f"emoji_features_{version}.npy", np.stack(features, axis=0).astype(np.float32))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, default=Path("app/assets/twemoji_png"))
    parser.add_argument("--output", type=Path, default=Path("app/data"))
    parser.add_argument("--version", type=str, default="v1")
    args = parser.parse_args()

    build_dataset(args.assets, args.output, args.version)


if __name__ == "__main__":
    main()
