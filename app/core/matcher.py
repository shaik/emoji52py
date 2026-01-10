from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np

from app.core.cache import FeatureCacheKey, FeatureMemoCache


@dataclass(frozen=True)
class MatchWeights:
    color: float = 1.0
    edge: float = 0.2
    alpha: float = 0.1


def _compute_distances(
    features: np.ndarray,
    target: np.ndarray,
    weights: MatchWeights,
) -> np.ndarray:
    color_diff = features[:, 0:3] - target[0:3]
    color_dist = np.sum(color_diff ** 2, axis=1)
    edge_diff = features[:, 3] - target[3]
    alpha_diff = features[:, 4] - target[4]
    return (
        weights.color * color_dist
        + weights.edge * (edge_diff ** 2)
        + weights.alpha * (alpha_diff ** 2)
    )


def _quantize_feature(target: np.ndarray) -> FeatureCacheKey:
    lab = (int(round(target[0] / 2)), int(round(target[1] / 2)), int(round(target[2] / 2)))
    edge = int(round(target[3] * 100))
    alpha = int(round(target[4] * 100))
    return FeatureCacheKey(lab=lab, edge=edge, alpha=alpha)


def match_features(
    cell_features: np.ndarray,
    emoji_features: np.ndarray,
    weights: MatchWeights,
    deterministic: bool,
    rng: Optional[random.Random] = None,
    memo_cache: Optional[FeatureMemoCache] = None,
    epsilon: float = 1e-6,
) -> np.ndarray:
    if deterministic and rng is None:
        rng = random.Random(0)

    indices = np.empty((cell_features.shape[0],), dtype=np.int32)

    for i, target in enumerate(cell_features):
        cached = None
        cache_key = None
        if memo_cache is not None:
            cache_key = _quantize_feature(target)
            cached = memo_cache.get(cache_key)
        if cached is not None:
            indices[i] = cached
            continue

        distances = _compute_distances(emoji_features, target, weights)
        min_dist = distances.min()
        candidates = np.where(distances <= min_dist + epsilon)[0]
        if len(candidates) == 1 or not deterministic:
            choice = int(candidates[0])
        else:
            choice = int(rng.choice(list(candidates)))
        indices[i] = choice
        if memo_cache is not None and cache_key is not None:
            memo_cache.set(cache_key, choice)

    return indices
