import random

from PIL import Image

from app.core.dataset import load_dataset
from app.core.features import compute_grid_features
from app.core.matcher import MatchWeights, match_features


def test_golden_blue_match():
    dataset = load_dataset("v1")
    target_emoji = chr(int("1f30a", 16))
    assert target_emoji in dataset.emoji_list

    image = Image.new("RGBA", (20, 20), color=(60, 140, 220, 255))
    cell_features, _, _, _ = compute_grid_features(image, grid_w=2, grid_h=2)

    rng = random.Random(123)
    indices = match_features(cell_features, dataset.features, MatchWeights(), deterministic=True, rng=rng)
    grid = [
        [dataset.emoji_list[idx] for idx in indices[0:2]],
        [dataset.emoji_list[idx] for idx in indices[2:4]],
    ]

    assert all(cell == target_emoji for row in grid for cell in row)
