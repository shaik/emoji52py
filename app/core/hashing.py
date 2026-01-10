from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(image_bytes: bytes, crop: dict[str, int], settings: dict[str, Any], dataset_version: str) -> str:
    payload = {
        "crop": crop,
        "settings": settings,
        "dataset_version": dataset_version,
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    hasher = hashlib.blake2b(digest_size=16)
    hasher.update(image_bytes)
    hasher.update(payload_bytes)
    return hasher.hexdigest()


def deterministic_seed(image_bytes: bytes, crop: dict[str, int], settings: dict[str, Any], dataset_version: str) -> int:
    payload = {
        "crop": crop,
        "settings": settings,
        "dataset_version": dataset_version,
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    hasher = hashlib.blake2b(digest_size=8)
    hasher.update(image_bytes)
    hasher.update(payload_bytes)
    return int.from_bytes(hasher.digest(), "big", signed=False)
