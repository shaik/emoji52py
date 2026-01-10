import random

import numpy as np

from app.core.matcher import MatchWeights, match_features


def test_match_features_deterministic_tie():
    emoji_features = np.array(
        [
            [10.0, 0.0, 0.0, 0.0, 1.0],
            [10.0, 0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    cell_features = np.array([[10.0, 0.0, 0.0, 0.0, 1.0]], dtype=np.float32)
    rng = random.Random(123)
    weights = MatchWeights()
    first = match_features(cell_features, emoji_features, weights, deterministic=True, rng=rng)

    rng = random.Random(123)
    second = match_features(cell_features, emoji_features, weights, deterministic=True, rng=rng)

    assert first[0] == second[0]
